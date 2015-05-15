# coding: utf-8
"""Backend management system classes

Used to communicate with providers without using CFME facilities
"""
import fauxfactory
from ovirtsdk.api import API
from ovirtsdk.infrastructure.errors import DisconnectedError
from ovirtsdk.xml import params

from cfme import exceptions as cfme_exc
from utils.log import logger
from utils.mgmt_system.base import MgmtSystemAPIBase, VMInfo
from utils.mgmt_system.exceptions import (
    VMInstanceNotFound, VMInstanceNotSuspended
)
from utils.wait import wait_for, TimedOutError


class RHEVMSystem(MgmtSystemAPIBase):
    """
    Client to RHEVM API

    This class piggy backs off ovirtsdk.

    Benefits of ovirtsdk:

    * Don't need intimite knowledge w/ RHEVM api itself.

    Detriments of ovirtsdk:

    * Response to most quaries are returned as an object rather than a string.
      This makes it harder to do simple stuff like getting the status of a vm.
    * Because of this, it makes listing VMs based on \*\*kwargs impossible
      since ovirtsdk relies on re class to find matches.

      * | For example: List out VM with this name (positive case)
        | Ideal: self.api.vms.list(name='test_vm')
        | Underneath the hood:

        * ovirtsdk fetches list of all vms [ovirtsdk.infrastructure.brokers.VM
          object, ...]
        * ovirtsdk then tries to filter the result using re.

          * tries to look for 'name' attr in ovirtsdk.infrastructure.brokers.VM
            object
          * found name attribute, in this case, the type of the value of the
            attribute is string.
          * match() succeed in comparing the value to 'test_vm'

      * | For example: List out VM with that's powered on (negative case)
        | Ideal: self.api.vms.list(status='up')
        | Underneath the hood:

        * **same step as above except**

          * found status attribute, in this case, the type of the value of
            the attribute is ovirtsdk.xml.params.Status
          * match() failed because class is compared to string 'up'

     This problem should be attributed to how RHEVM api was designed rather
     than how ovirtsdk handles RHEVM api responses.

    * Obj. are not updated after action calls.

      * For example::
          vm = api.vms.get(name='test_vm')
          vm.status.get_state() # returns 'down'
          vm.start()
          # wait a few mins
          vm.status.get_state() # returns 'down'; wtf?

          vm = api.vms.get(name='test_vm')
          vm.status.get_state() # returns 'up'

    Args:
        hostname: The hostname of the system.
        username: The username to connect with.
        password: The password to connect with.

    Returns: A :py:class:`RHEVMSystem` object.
    """

    _stats_available = {
        'num_vm': lambda self: self.api.get_summary().get_vms().total,
        'num_host': lambda self: len(self.list_host()),
        'num_cluster': lambda self: len(self.list_cluster()),
        'num_template': lambda self: len(self.list_template()),
        'num_datastore': lambda self: len(self.list_datastore()),
    }

    STEADY_WAIT_MINS = 6

    def __init__(self, hostname, username, password, **kwargs):
        # generate URL from hostname

        if 'port' in kwargs:
            url = 'https://%s:%s/api' % (hostname, kwargs['port'])
        else:
            url = 'https://%s/api' % hostname

        self._api = None
        self._api_kwargs = {
            'url': url,
            'username': username,
            'password': password,
            'insecure': True
        }
        self.kwargs = kwargs

    @property
    def api(self):
        # test() will return false if the connection timeouts, catch it and force it to re-init
        try:
            if self._api is None or (self._api is not None and not self._api.test()):
                self._api = API(**self._api_kwargs)
        # if the connection was disconnected, force it to re-init
        except DisconnectedError:
            self._api = API(**self._api_kwargs)
        return self._api

    def _get_vm(self, vm_name=None):
        """ Returns a vm from the RHEVM object.

        Args:
            vm_name: The name of the VM.

        Returns: an ovirtsdk vm object.
        """
        if vm_name is None:
            raise VMInstanceNotFound(vm_name)
        else:
            vm = self.api.vms.get(name=vm_name)
            if vm is None:
                raise VMInstanceNotFound(vm_name)
            return vm

    def current_ip_address(self, vm_name):
        info = self._get_vm(vm_name).get_guest_info()
        if info is None:
            return None
        try:
            return info.get_ips().get_ip()[0].get_address()
        except (AttributeError, IndexError):
            return None

    def get_ip_address(self, vm_name, timeout=600):
        try:
            return wait_for(lambda: self.current_ip_address(vm_name),
                fail_condition=None, delay=5, num_sec=timeout,
                message="get_ip_address from rhevm")[0]
        except TimedOutError:
            return None

    def get_vm_name_from_ip(self, ip):
        # unfortunately it appears you cannot query for ip address from the sdk,
        #   unlike curling rest api which does work
        """ Gets the name of a vm from its IP.

        Args:
            ip: The ip address of the vm.
        Returns: The vm name for the corresponding IP."""

        vms = self.api.vms.list()

        for vm in vms:
            if vm.get_guest_info() is None or vm.get_guest_info().get_ips() is None:
                continue
            else:
                for addr in vm.get_guest_info().get_ips().get_ip():
                    if ip in addr.get_address():
                        return vm.name
        raise cfme_exc.VmNotFoundViaIP('The requested IP is not known as a VM')

    def does_vm_exist(self, name):
        try:
            self._get_vm(name)
            return True
        except VMInstanceNotFound:
            return False

    def start_vm(self, vm_name=None):
        self.wait_vm_steady(vm_name)
        logger.info(' Starting RHEV VM %s' % vm_name)
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'up':
            logger.info(' RHEV VM %s os already running.' % vm_name)
            return True
        else:
            vm.start()
            self.wait_vm_running(vm_name)
            return True

    def stop_vm(self, vm_name):
        self.wait_vm_steady(vm_name)
        logger.info(' Stopping RHEV VM %s' % vm_name)
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'down':
            logger.info(' RHEV VM %s os already stopped.' % vm_name)
            return True
        else:
            vm.stop()
            self.wait_vm_stopped(vm_name)
            return True

    def delete_vm(self, vm_name):
        self.wait_vm_steady(vm_name)
        vm = self._get_vm(vm_name)
        if not self.is_vm_stopped(vm_name):
            self.stop_vm(vm_name)
        logger.debug(' Deleting RHEV VM %s' % vm_name)
        vm.delete()
        wait_for(
            lambda: self.does_vm_exist(vm_name),
            fail_condition=True,
            message="wait for RHEV VM %s deleted" % vm_name,
            num_sec=300
        )
        return True

    def create_vm(self, vm_name):
        raise NotImplementedError('This function has not yet been implemented.')
    # Heres the code but don't have a need and no time to test it to get it right
    #   including for inclusion later
    #
    # def create_vm(self, vm_name, *args, **kwargs):
    #     MB = 1024 * 1024
    #     try:
    #         self.api.vms.add(
    #             params.VM(
    #                 name=vm_name,
    #                 memory=kwargs['memory_in_mb'] * MB,
    #                 cluster=self.api.clusters.get(kwargs['cluster_name']),
    #                 template=self.api.templates.get('Blank')))
    #         print 'VM created'
    #         self.api.vms.get(vm_name).nics.add(params.NIC(name='eth0',
    #             network=params.Network(name='ovirtmgmt'), interface='virtio'))
    #         print 'NIC added to VM'
    #         self.api.vms.get(vm_name).disks.add(params.Disk(
    #             storage_domains=params.StorageDomains(
    #                 storage_domain=[self.api.storagedomains.get(kwargs['storage_domain'])],
    #                 size=512 * MB,
    #                 status=None,
    #                 interface='virtio',
    #                 format='cow',
    #                 sparse=True,
    #                 bootable=True)))
    #         print 'Disk added to VM'
    #         print 'Waiting for VM to reach Down status'
    #         while self.api.vms.get(vm_name).status.state != 'down':
    #             time.sleep(1)
    #     except Exception as e:
    #         print 'Failed to create VM with disk and NIC\n%s' % str(e)

    def restart_vm(self, vm_name):
        logger.debug(' Restarting RHEV VM %s' % vm_name)
        return self.stop_vm(vm_name) and self.start_vm(vm_name)

    def list_vm(self, **kwargs):
        # list vm based on kwargs can be buggy
        # i.e. you can't return a list of powered on vm
        # but you can return a vm w/ a matched name
        vm_list = self.api.vms.list(**kwargs)
        return [vm.name for vm in vm_list]

    def all_vms(self):
        result = []
        for vm in self.api.vms.list():
            try:
                ip = vm.get_guest_info().get_ips().get_ip()[0].get_address()
            except (AttributeError, IndexError):
                ip = None
            result.append(
                VMInfo(
                    vm.get_id(),
                    vm.get_name(),
                    vm.get_status().get_state(),
                    ip,
                )
            )
        return result

    def list_host(self, **kwargs):
        host_list = self.api.hosts.list(**kwargs)
        return [host.name for host in host_list]

    def list_datastore(self, **kwargs):
        datastore_list = self.api.storagedomains.list(**kwargs)
        return [ds.name for ds in datastore_list if ds.get_status() is None]

    def list_cluster(self, **kwargs):
        cluster_list = self.api.clusters.list(**kwargs)
        return [cluster.name for cluster in cluster_list]

    def list_template(self, **kwargs):
        """
        Note: CFME ignores the 'Blank' template, so we do too
        """
        template_list = self.api.templates.list(**kwargs)
        return [template.name for template in template_list if template.name != "Blank"]

    def list_flavor(self):
        raise NotImplementedError('This function is not supported on this platform.')

    def info(self):
        # and we got nothing!
        pass

    def disconnect(self):
        self.api.disconnect()

    def vm_status(self, vm_name=None):
        return self._get_vm(vm_name).get_status().get_state()

    def vm_creation_time(self, vm_name):
        vm = self._get_vm(vm_name)
        return vm.get_creation_time().replace(tzinfo=None)

    def in_steady_state(self, vm_name):
        return self.vm_status(vm_name) in {"up", "down", "suspended"}

    def is_vm_running(self, vm_name):
        return self.vm_status(vm_name) == "up"

    def wait_vm_running(self, vm_name, num_sec=360):
        logger.info(" Waiting for RHEV-M VM %s to change status to ON" % vm_name)
        wait_for(self.is_vm_running, [vm_name], num_sec=num_sec)

    def is_vm_stopped(self, vm_name):
        return self.vm_status(vm_name) == "down"

    def wait_vm_stopped(self, vm_name, num_sec=360):
        logger.info(" Waiting for RHEV-M VM %s to change status to OFF" % vm_name)
        wait_for(self.is_vm_stopped, [vm_name], num_sec=num_sec)

    def is_vm_suspended(self, vm_name):
        return self.vm_status(vm_name) == "suspended"

    def wait_vm_suspended(self, vm_name, num_sec=720):
        logger.info(" Waiting for RHEV-M VM %s to change status to SUSPENDED" % vm_name)
        wait_for(self.is_vm_suspended, [vm_name], num_sec=num_sec)

    def suspend_vm(self, vm_name):
        self.wait_vm_steady(vm_name)
        logger.debug(' Suspending RHEV VM %s' % vm_name)
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'down':
            raise VMInstanceNotSuspended(vm_name)
        elif vm.status.get_state() == 'suspended':
            logger.info(' RHEV VM %s is already suspended.' % vm_name)
            return True
        else:
            vm.suspend()
            self.wait_vm_suspended(vm_name)
            return True

    def clone_vm(self, source_name, vm_name):
        raise NotImplementedError('This function has not yet been implemented.')

    def deploy_template(self, template, *args, **kwargs):
        logger.debug(' Deploying RHEV template %s to VM %s' % (template, kwargs["vm_name"]))
        timeout = kwargs.pop('timeout', 900)
        power_on = kwargs.pop('power_on', True)
        vm_kwargs = {
            'name': kwargs['vm_name'],
            'cluster': self.api.clusters.get(kwargs['cluster']),
            'template': self.api.templates.get(template)
        }
        if 'placement_policy_host' in kwargs and 'placement_policy_affinity' in kwargs:
            host = params.Host(name=kwargs['placement_policy_host'])
            policy = params.VmPlacementPolicy(host=host,
                affinity=kwargs['placement_policy_affinity'])
            vm_kwargs['placement_policy'] = policy
        vm = params.VM(**vm_kwargs)
        self.api.vms.add(vm)
        self.wait_vm_stopped(kwargs['vm_name'], num_sec=timeout)
        if power_on:
            self.start_vm(kwargs['vm_name'])
        return kwargs['vm_name']

    def remove_host_from_cluster(self, hostname):
        raise NotImplementedError('remove_host_from_cluster not implemented')

    def mark_as_template(
            self, vm_name, delete=True, temporary_name=None, delete_on_error=True, **kwargs):
        """Turns the VM off, creates template from it and deletes the original VM.

        Mimics VMware behaviour here.

        Args:
            vm_name: Name of the VM to be turned to template
            delete: Whether to delete the VM (default: True)
            temporary_name: If you want, you can specific an exact temporary name for renaming.
        """
        temp_template_name = temporary_name or "templatize_{}".format(
            fauxfactory.gen_alphanumeric(8))
        try:
            with self.steady_wait(30):
                create_new_template = True
                if self.does_template_exist(temp_template_name):
                    try:
                        self._wait_template_ok(temp_template_name)
                    except VMInstanceNotFound:
                        pass  # It got deleted.
                    else:
                        create_new_template = False
                        if self.does_vm_exist(vm_name) and delete:
                            self.delete_vm(vm_name)
                        if delete:  # We can only rename to the original name if we delete the vm
                            self._rename_template(temp_template_name, vm_name)

                if create_new_template:
                    self.stop_vm(vm_name)
                    vm = self._get_vm(vm_name)
                    actual_cluster = vm.get_cluster()
                    new_template = params.Template(
                        name=temp_template_name, vm=vm, cluster=actual_cluster)
                    self.api.templates.add(new_template)
                    # First it has to appear
                    self._wait_template_exists(temp_template_name)
                    # Then the process has to finish
                    self._wait_template_ok(temp_template_name)
                    # Delete the original VM
                    if self.does_vm_exist(vm_name) and delete:
                        self.delete_vm(vm_name)
                    if delete:  # We can only rename to the original name if we delete the vm
                        self._rename_template(temp_template_name, vm_name)
        except TimedOutError:
            if delete_on_error:
                self.delete_template(temp_template_name)
            raise

    def _rename_template(self, old_name, new_name):
        template = self.api.templates.get(name=old_name)
        if template is None:
            raise VMInstanceNotFound("Template {} not found!".format(old_name))
        template.set_name(new_name)
        template.update()

    def rename_vm(self, vm_name, new_vm_name):
        vm = self._get_vm(vm_name)
        try:
            vm.set_name(new_vm_name)
            vm.update()
        except Exception as e:
            logger.exception(e)
            return vm_name
        else:
            return new_vm_name

    def _wait_template_ok(self, template_name):
        try:
            wait_for(
                lambda:
                self.api.templates.get(name=template_name).get_status().state == "ok",
                num_sec=30 * 60, message="template is OK", delay=45)
        except AttributeError:  # .get() returns None when template not found
            raise VMInstanceNotFound("Template {} not found!".format(template_name))

    def _wait_template_exists(self, template_name):
        wait_for(
            lambda: self.does_template_exist(template_name),
            num_sec=30 * 60, message="template exists", delay=45)

    def does_template_exist(self, template_name):
        return self.api.templates.get(name=template_name) is not None

    def delete_template(self, template_name):
        template = self.api.templates.get(name=template_name)
        if template is None:
            logger.info(
                " Template {} is already not present on the RHEV-M provider".format(template_name))
            return
        self._wait_template_ok(template_name)
        template.delete()
        wait_for(
            lambda: not self.does_template_exist(template_name),
            num_sec=15 * 60, delay=20)
