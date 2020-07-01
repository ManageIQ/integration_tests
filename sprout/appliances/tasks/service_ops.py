from celery import chain
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from wrapanapi import Openshift

from . import singleton_task, provider_error_logger
from .maintainance import sync_provider_hw, sync_appliance_hw
from appliances.models import Provider, Appliance


@singleton_task()
def appliance_power_on(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        # source objects are not present
        return
    try:
        if not appliance.provider.is_working:
            raise RuntimeError('Provider {} is not working.'.format(appliance.provider))
        # TODO: change after openshift wrapanapi refactor
        # we could use vm.ensure_state(VmState.RUNNING) here in future
        if appliance.is_openshift:
            vm_running = appliance.provider_api.is_vm_running(appliance.name)
            vm_steady = appliance.provider_api.in_steady_state(appliance.name)
        else:
            vm_running = appliance.vm_mgmt.is_running
            vm_steady = appliance.vm_mgmt.in_steady_state
        if vm_running:
            appliance.set_status("Appliance was powered on.")

            with transaction.atomic():
                appliance = Appliance.objects.get(id=appliance_id)
                appliance.set_power_state(Appliance.Power.ON)
                appliance.save()
            if appliance.containerized and not appliance.is_openshift:
                with appliance.ipapp.ssh_client as ssh:
                    # Fire up the container
                    ssh.run_command('cfme-start', ensure_host=True)
                # VM is running now.
            sync_appliance_hw.delay(appliance.id)
            sync_provider_hw.delay(appliance.template.provider.id)
            return
        elif not vm_steady:
            # TODO: change after openshift wrapanapi refactor
            if appliance.is_openshift:
                current_state = appliance.provider_api.vm_status(appliance.name)
            else:
                current_state = appliance.vm_mgmt.state
            appliance.set_status("Waiting for appliance to be steady (current state: {}).".format(
                current_state))
            self.retry(args=(appliance_id,), countdown=20, max_retries=40)
        else:
            appliance.set_status("Powering on.")
            # TODO: change after openshift wrapanapi refactor
            if appliance.is_openshift:
                appliance.provider_api.start_vm(appliance.name)
            else:
                appliance.vm_mgmt.start()
            self.retry(args=(appliance_id,), countdown=20, max_retries=40)
    except Exception as ex:
        provider_error_logger().error("Exception {}: {}".format(type(ex).__name__, str(ex)))
        self.retry(args=(appliance_id,), exc=ex, countdown=20, max_retries=30)


@singleton_task()
def appliance_yum_update(self, appliance_id):
    appliance = Appliance.objects.get(id=appliance_id)
    appliance.ipapp.update_rhel(reboot=False)


@singleton_task()
def appliance_reboot(self, appliance_id, if_needs_restarting=False):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        # source objects are not present
        return
    try:
        if if_needs_restarting:
            with appliance.ssh as ssh:
                if int(ssh.run_command("needs-restarting | wc -l").output.strip()) == 0:
                    return  # No reboot needed
        with transaction.atomic():
            appliance = Appliance.objects.get(id=appliance_id)
            appliance.set_power_state(Appliance.Power.REBOOTING)
            appliance.save()
        appliance.ipapp.reboot(wait_for_miq_ready=False, log_callback=appliance.set_status)
        with transaction.atomic():
            appliance = Appliance.objects.get(id=appliance_id)
            appliance.set_power_state(Appliance.Power.ON)
            appliance.save()
    except Exception as e:
        provider_error_logger().error("Exception {}: {}".format(type(e).__name__, str(e)))
        self.retry(args=(appliance_id,), exc=e, countdown=20, max_retries=30)


@singleton_task()
def kill_appliance(self, appliance_id, replace_in_pool=False, minutes=60):
    """As-reliable-as-possible appliance deleter. Turns off, deletes the VM and deletes the object.

    If the appliance was assigned to pool and we want to replace it, redo the provisioning.
    """
    self.logger.info("Initiated kill of appliance {}".format(appliance_id))
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist as e:
        self.logger.error("It seems such appliance %s doesn't exist: %s", appliance_id, str(e))
        return False

    workflow = [
        disconnect_direct_lun.si(appliance_id),
        appliance_power_off.si(appliance_id),
        kill_appliance_delete.si(appliance_id),
    ]
    if replace_in_pool:
        from .provisioning import replace_clone_to_pool
        if appliance.appliance_pool is not None:
            workflow.append(
                replace_clone_to_pool.si(
                    appliance.template.version, appliance.template.date,
                    appliance.appliance_pool.id, minutes, appliance.template.id))
    workflow = chain(*workflow)
    workflow()


@singleton_task()
def disconnect_direct_lun(self, appliance_id):
    self.logger.info("Disconnect direct lun has been started for {}".format(appliance_id))
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist as e:
        self.logger.error("It seems such appliance %s doesn't exist: %s", appliance_id, str(e))
        return False

    if not appliance.provider.is_working:
        raise RuntimeError('Provider {} is not working for appliance {}'
                           .format(appliance.provider, appliance.name))
    if not appliance.lun_disk_connected:
        return False
    # TODO: change after openshift wrapanapi refactor
    if not appliance.is_openshift and not hasattr(appliance.vm_mgmt, "disconnect_disk"):
        return False
    try:
        # TODO: we need a disk name to disconnect, fix this method call.
        appliance.vm_mgmt.disconnect_disk('na')
    except Exception as e:
        appliance.set_status("LUN: {}: {}".format(type(e).__name__, str(e)))
        return False
    else:
        appliance.reload()
        with transaction.atomic():
            appliance.lun_disk_connected = False
            appliance.save(update_fields=['lun_disk_connected'])
        return True


@singleton_task()
def appliance_power_off(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        # source objects are not present
        return
    try:
        if not appliance.provider.is_working:
            raise RuntimeError('Provider {} is not working.'.format(appliance.provider))
        prov_api = appliance.provider_api
        # TODO: change after openshift wrapanapi refactor
        # we could use vm.ensure_state(VmState.STOPPED) here in future
        vm_exists = False
        if prov_api.does_vm_exist(appliance.name):
            vm_exists = True
            if appliance.is_openshift:
                vm_stopped = prov_api.is_vm_stopped(appliance.name)
                vm_suspended = prov_api.is_vm_suspended(appliance.name)
                vm_steady = prov_api.in_steady_state(appliance.name)
            else:
                vm_stopped = appliance.vm_mgmt.is_stopped
                vm_suspended = appliance.vm_mgmt.is_suspended
                vm_steady = appliance.vm_mgmt.in_steady_state
        if not vm_exists or vm_stopped:
            Appliance.objects.get(id=appliance_id).set_status("Appliance was powered off.")
            with transaction.atomic():
                appliance = Appliance.objects.get(id=appliance_id)
                appliance.set_power_state(Appliance.Power.OFF)
                appliance.ready = False
                appliance.save()
            sync_provider_hw.delay(appliance.template.provider.id)
            return
        elif vm_suspended:
            appliance.set_status("Starting appliance from suspended state to properly off it.")
            # TODO: change after openshift wrapanapi refactor
            if appliance.is_openshift:
                prov_api.start_vm(appliance.name)
            else:
                appliance.vm_mgmt.start()
            self.retry(args=(appliance_id,), countdown=20, max_retries=40)
        elif not vm_steady:
            # TODO: change after openshift wrapanapi refactor
            if appliance.is_openshift:
                vm_status = prov_api.vm_status(appliance.name)
            else:
                vm_status = appliance.vm_mgmt.state
            appliance.set_status("Waiting for appliance to be steady (current state: {}).".format(
                vm_status))
            self.retry(args=(appliance_id,), countdown=20, max_retries=40)
        else:
            appliance.set_status("Powering off.")
            # TODO: change after openshift wrapanapi refactor
            if appliance.is_openshift:
                prov_api.stop_vm(appliance.name)
            else:
                appliance.vm_mgmt.stop()
            self.retry(args=(appliance_id,), countdown=20, max_retries=40)
    except Exception as e:
        provider_error_logger().error("Exception {}: {}".format(type(e).__name__, str(e)))
        self.retry(args=(appliance_id,), exc=e, countdown=20, max_retries=40)


@singleton_task()
def appliance_suspend(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        # source objects are not present
        return
    try:
        if not appliance.provider.is_working:
            raise RuntimeError('Provider {} is not working.'.format(appliance.provider))
        # TODO: change after openshift wrapanapi refactor
        # we could use vm.ensure_state(VmState.SUSPENDED) here in future
        prov_api = appliance.provider_api
        if appliance.is_openshift:
            vm_suspended = prov_api.is_vm_suspended(appliance.name)
            vm_steady = prov_api.in_steady_state(appliance.name)
        else:
            vm_suspended = appliance.vm_mgmt.is_suspended
            vm_steady = appliance.vm_mgmt.in_steady_state
        if vm_suspended:
            Appliance.objects.get(id=appliance_id).set_status("Appliance was suspended.")
            with transaction.atomic():
                appliance = Appliance.objects.get(id=appliance_id)
                appliance.set_power_state(Appliance.Power.SUSPENDED)
                appliance.ready = False
                appliance.save()
            sync_provider_hw.delay(appliance.template.provider.id)
            return
        elif not vm_steady:
            # TODO: change after openshift wrapanapi refactor
            if appliance.is_openshift:
                vm_status = prov_api.vm_status(appliance.name)
            else:
                vm_status = appliance.vm_mgmt.state
            appliance.set_status("Waiting for appliance to be steady (current state: {}).".format(
                vm_status))
            self.retry(args=(appliance_id,), countdown=20, max_retries=30)
        else:
            appliance.set_status("Suspending.")
            # TODO: change after openshift wrapanapi refactor
            if appliance.is_openshift:
                prov_api.suspend_vm(appliance.name)
            else:
                appliance.vm_mgmt.suspend()
            self.retry(args=(appliance_id,), countdown=20, max_retries=30)
    except Exception as e:
        provider_error_logger().error("Exception {}: {}".format(type(e).__name__, str(e)))
        self.retry(args=(appliance_id,), exc=e, countdown=20, max_retries=30)


@singleton_task()
def connect_direct_lun(self, appliance_id):
    appliance = Appliance.objects.get(id=appliance_id)
    if not appliance.provider.is_working:
        raise RuntimeError('Provider {} is not working.'.format(appliance.provider))
    # TODO: change after openshift wrapanapi refactor
    if not appliance.is_openshift and not hasattr(appliance.vm_mgmt, "connect_direct_lun"):
        return False
    try:
        # TODO: connect_direct_lun needs args, fix this method call.
        appliance.vm_mgmt.connect_direct_lun()
    except Exception as e:
        appliance.set_status("LUN: {}: {}".format(type(e).__name__, str(e)))
        return False
    else:
        appliance.reload()
        with transaction.atomic():
            appliance.lun_disk_connected = True
            appliance.save(update_fields=['lun_disk_connected'])
        return True


@singleton_task()
def kill_appliance_delete(self, appliance_id, _delete_already_issued=False):
    delete_issued = False
    try:
        appliance = Appliance.objects.get(id=appliance_id)
        self.logger.info("Trying to kill appliance {}/{}".format(appliance_id, appliance.name))
        if not appliance.provider.is_working:
            self.logger.error('Provider {} is not working for appliance {}'
                              .format(appliance.provider, appliance.name))
            raise RuntimeError('Provider {} is not working for appliance {}'
                               .format(appliance.provider, appliance.name))
        if appliance.provider_api.does_vm_exist(appliance.name):
            appliance.set_status("Deleting the appliance from provider")
            # If we haven't issued the delete order, do it now
            if not _delete_already_issued:
                # TODO: change after openshift wrapanapi refactor
                self.logger.info(
                    "Calling provider's remove appliance method {}".format(appliance_id))
                if isinstance(appliance.provider_api, Openshift):
                    appliance.provider_api.delete_vm(appliance.name)
                else:
                    appliance.vm_mgmt.cleanup()
                delete_issued = True
            # In any case, retry to wait for the VM to be deleted, but next time do not issue delete
            self.retry(args=(appliance_id, True), countdown=5, max_retries=60)
        self.logger.info("Removing appliance from database {}".format(appliance_id))
        appliance.delete()
    except ObjectDoesNotExist:
        self.logger.error("Can't kill appliance {}. it doesn't exist".format(appliance_id))
        # Appliance object already not there
        return
    except Exception as e:
        try:
            self.logger.error("Could not delete appliance {}. Retrying".format(appliance_id))
            appliance.set_status("Could not delete appliance. Retrying.")
        except UnboundLocalError:
            self.logger.error("Could not delete appliance {}. Some error "
                              "happened".format(appliance_id))
            return  # The appliance is not there any more
        # In case of error retry, and also specify whether the delete order was already issued
        self.retry(
            args=(appliance_id, _delete_already_issued or delete_issued),
            exc=e, countdown=5, max_retries=60)


@singleton_task()
def anyvm_power_on(self, provider, vm):
    provider = Provider.objects.get(id=provider, working=True, disabled=False)
    # TODO: change after openshift wrapanapi refactor
    if isinstance(provider.api, Openshift):
        provider.api.start_vm(vm)
    else:
        provider.api.get_vm(vm).start()


@singleton_task()
def anyvm_power_off(self, provider, vm):
    provider = Provider.objects.get(id=provider, working=True, disabled=False)
    # TODO: change after openshift wrapanapi refactor
    if isinstance(provider.api, Openshift):
        provider.api.stop_vm(vm)
    else:
        provider.api.get_vm(vm).stop()


@singleton_task()
def anyvm_suspend(self, provider, vm):
    provider = Provider.objects.get(id=provider, working=True, disabled=False)
    # TODO: change after openshift wrapanapi refactor
    if isinstance(provider.api, Openshift):
        provider.api.suspend_vm(vm)
    else:
        provider.api.get_vm(vm).suspend()


@singleton_task()
def anyvm_delete(self, provider, vm):
    provider = Provider.objects.get(id=provider, working=True, disabled=False)
    # TODO: change after openshift wrapanapi refactor
    if isinstance(provider.api, Openshift):
        provider.api.delete_vm(vm)
    else:
        provider.api.get_vm(vm).cleanup()
