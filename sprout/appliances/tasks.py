# -*- coding: utf-8 -*-
from __future__ import absolute_import

import random
import re
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone
from celery import chain, shared_task
from celery.signals import celeryd_init
from datetime import timedelta

from appliances.models import Provider, Group, Template, Appliance, AppliancePool
from sprout import settings
from sprout.celery import app as celery_app

from utils.appliance import Appliance as CFMEAppliance
from utils.randomness import generate_random_string
from utils.trackerbot import api, parse_template


LOCK_EXPIRE = 60 * 5
VERSION_REGEXPS = [
    # 4 digits
    r"cfme-(\d)(\d)(\d)(\d)-",      # cfme-5242-    -> 5.2.4.2
    r"cfme-(\d)(\d)(\d)-(\d)-",     # cfme-520-1-   -> 5.2.0.1
    # 5 digits  (not very intelligent but no better solution so far)
    r"cfme-(\d)(\d)(\d0)(\d)-",     # cfme-53101-   -> 5.3.10.1
    r"cfme-(\d)(\d)(\d)(\d{2})-",   # cfme-53111-   -> 5.3.1.11
]
VERSION_REGEXPS = map(re.compile, VERSION_REGEXPS)


def retrieve_cfme_appliance_version(template_name):
    """If possible, retrieve the appliance's version from template's name."""
    for regexp in VERSION_REGEXPS:
        match = regexp.search(template_name)
        if match is not None:
            return ".".join(match.groups())


def trackerbot():
    return api(settings.TRACKERBOT_URL)


def none_dict(l):
    """"If the parameter passed is None, returns empty dict. Otherwise it passes through"""
    if l is None:
        return {}
    else:
        return l


@celeryd_init.connect
def start_task(sender=None, conf=None, **kwargs):
    """This task is designed to kick off self-scheduling periodical tasks at the beginning of the
    run. I used beat service for them before, but this solution guarantees there will be no overlap.
    Something like singleton."""
    def schedule(t, *args, **kwargs):
        """Checks if the task is not scheduled yet. If so, it is scheduled, otherwise not. This
        should enforce that there aren't two or more instances of the same task running."""
        info = celery_app.control.inspect()
        found = False
        # Check active
        for task_list in none_dict(info.active()).values():
            for task in task_list:
                if task["name"] == t.name:
                    found = True
        # Check scheduled
        for task_list in none_dict(info.scheduled()).values():
            for task in task_list:
                if task["request"]["name"] == t.name:
                    found = True
        # Check reserved
        for task_list in none_dict(info.reserved()).values():
            for task in task_list:
                if task["request"]["name"] == t.name:
                    found = True

        # Schedule if it is not there
        if not found:
            return t.apply_async(*args, **kwargs)
        else:
            return None

    schedule(retrieve_appliances_power_states, countdown=15)
    schedule(free_appliance_shepherd, countdown=30)
    schedule(kill_unused_appliances, countdown=40)
    schedule(delete_nonexistent_appliances, countdown=60)
    schedule(poke_providers, countdown=5)
    schedule(poke_trackerbot, countdown=25)
    schedule(retrieve_template_existence, countdown=35)


@shared_task(bind=True)
def poke_providers(self):
    """Basic tasks that checks whether to connections to providers work."""
    try:
        with transaction.atomic():
            for provider in Provider.objects.all():
                try:
                    provider.api.list_vm()
                except:
                    provider.working = False
                    provider.save()
                else:
                    provider.working = True
                    provider.save()
    finally:
        self.apply_async(countdown=180)


@shared_task(bind=True)
def kill_unused_appliances(self):
    """This is the watchdog, that guards the appliances that were given to users. If you forget
    to prolong the lease time, this is the thing that will take the appliance off your hands
    and kill it."""
    try:
        with transaction.atomic():
            for appliance in Appliance.objects.filter(marked_for_deletion=False, ready=True):
                if appliance.leased_until is not None and appliance.leased_until <= timezone.now():
                    kill_appliance.delay(appliance.id)
    finally:
        self.apply_async(countdown=80)


@shared_task
def kill_appliance(appliance_id, replace_in_pool=False, minutes=60):
    """As-reliable-as-possible appliance deleter. Turns off, deletes the VM and deletes the object.

    If teh appliance was assigned to pool and we want to replace it, redo the provisioning.
    """
    workflow = [
        appliance_power_off.si(appliance_id),
        kill_appliance_delete.si(appliance_id),
    ]
    if replace_in_pool:
        appliance = Appliance.objects.get(id=appliance_id)
        if appliance.appliance_pool is not None:
            workflow.append(
                clone_template_to_pool.si(
                    appliance.source_template.id, appliance.appliance_pool.id, minutes))
    workflow = chain(*workflow)
    workflow()


@shared_task(bind=True)
def kill_appliance_delete(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
        if appliance.provider_api.does_vm_exist(appliance.name):
            appliance.set_status("Deleting")
            appliance.provider_api.delete_vm(appliance.name)
    except ObjectDoesNotExist:
        # Appliance object already not there
        return
    except Exception as e:
        try:
            appliance.set_status("Could not delete appliance. Retrying.")
        except UnboundLocalError:
            return  # The appliance is not there any more
        self.retry(args=(appliance_id,), exc=e, countdown=10, max_retries=5)
    else:
        appliance.delete()


@shared_task(bind=True)
def poke_trackerbot(self):
    """This beat-scheduled task periodically polls the trackerbot if there are some new templates.
    """
    try:
        for group in trackerbot().group().get()["objects"]:
            if not group["stream"]:
                continue
            providers = group["latest_template_providers"]
            template = group["latest_template"]
            name = group["name"]
            try:
                group_o = Group.objects.get(id=name)
            except ObjectDoesNotExist:
                group_o = Group(id=name)
                group_o.save()
            for provider in providers:
                if provider not in settings.PROVIDER_FILTER:
                    continue
                try:
                    provider_o = Provider.objects.get(id=provider)
                except ObjectDoesNotExist:
                    provider_o = Provider(id=provider)
                    provider_o.save()
                if not provider_o.working:
                    continue
                try:
                    Template.objects.get(
                        provider=provider_o, template_group=group_o, original_name=template)
                except ObjectDoesNotExist:
                    create_appliance_template.delay(provider_o.id, group_o.id, template)
    finally:
        self.apply_async(countdown=600)


@shared_task
def create_appliance_template(provider_id, group_id, template_name):
    """This task creates a template from a fresh CFME template. In case of fatal error during the
    operation, the template object is deleted to make sure the operation will be retried next time
    when poke_trackerbot runs."""
    provider = Provider.objects.get(id=provider_id)
    group = Group.objects.get(id=group_id)
    with transaction.atomic():
        try:
            Template.objects.get(
                template_group=group, provider=provider, original_name=template_name)
            return False
        except ObjectDoesNotExist:
            pass
        # Fire off the template preparation
        date = parse_template(template_name)[-1]
        template_version = retrieve_cfme_appliance_version(template_name)
        new_template_name = settings.TEMPLATE_FORMAT.format(
            group=group.id, date=date.strftime("%y%m%d"), rnd=generate_random_string())
        template = Template(
            provider=provider, template_group=group, name=new_template_name, date=date,
            version=template_version, original_name=template_name)
        template.save()
    workflow = chain(
        prepare_template_deploy.si(template.id),
        prepare_template_configure.si(template.id),
        prepare_template_network_setup.si(template.id),
        prepare_template_poweroff.si(template.id),
        prepare_template_finish.si(template.id),
    )
    workflow.link_error(prepare_template_delete_on_error.si(template.id))
    workflow()


@shared_task(bind=True)
def prepare_template_deploy(self, template_id):
    template = Template.objects.get(id=template_id)
    if template.is_created:
        return True
    try:
        if not template.is_created:
            template.set_status("Deploying the template.")
            template.provider_api.clone_vm(
                template.original_name, template.name, sparse=True, provision_timeout=30 * 60)
        else:
            template.set_status("Waiting for deployment to be finished.")
            template.provider_api.wait_vm_running(template.name)
    except Exception as e:
        template.set_status("Could not properly deploy the template. Retrying.")
        self.retry(args=(template_id,), exc=e, countdown=10, max_retries=5)
    else:
        template.set_status("Template deployed.")


@shared_task(bind=True)
def prepare_template_configure(self, template_id):
    template = Template.objects.get(id=template_id)
    template.set_status("Customization started.")
    appliance = CFMEAppliance(template.provider_name, template.name)
    try:
        appliance.configure(
            setup_fleece=False,
            log_callback=lambda s: template.set_status("Customization progress: {}".format(s)))
    except Exception as e:
        template.set_status("Could not properly configure the CFME. Retrying.")
        self.retry(args=(template_id,), exc=e, countdown=10, max_retries=5)
    else:
        template.set_status("Template configuration was done.")


@shared_task(bind=True)
def prepare_template_network_setup(self, template_id):
    template = Template.objects.get(id=template_id)
    template.set_status("Setting up network.")
    try:
        ssh = template.cfme.ipapp.ssh_client()
        ssh.run_command("rm -f /etc/udev/rules.d/70-persistent-net.rules")
        ssh.run_command("sed -i -r -e '/^HWADDR/d' /etc/sysconfig/network-scripts/ifcfg-eth0")
        ssh.run_command("sed -i -r -e '/^UUID/d' /etc/sysconfig/network-scripts/ifcfg-eth0")
    except Exception as e:
        template.set_status("Could not configure the network. Retrying.")
        self.retry(
            args=(template_id,), exc=e, countdown=10, max_retries=5)
    else:
        template.set_status("Network has been set up.")


@shared_task(bind=True)
def prepare_template_poweroff(self, template_id):
    template = Template.objects.get(id=template_id)
    template.set_status("Powering off")
    try:
        template.provider_api.stop_vm(template.name)
        template.provider_api.wait_vm_stopped(template.name)
    except Exception as e:
        template.set_status("Could not power off the appliance. Retrying.")
        self.retry(args=(template_id,), exc=e, countdown=10, max_retries=5)
    else:
        template.set_status("Powered off.")


@shared_task(bind=True)
def prepare_template_finish(self, template_id):
    template = Template.objects.get(id=template_id)
    template.set_status("Finishing template creation.")
    try:
        template.provider_api.mark_as_template(template.name)
        with transaction.atomic():
            template = Template.objects.get(id=template_id)
            template.ready = True
            template.save()
    except Exception as e:
        template.set_status("Could not mark the appliance as template. Retrying.")
        self.retry(args=(template_id,), exc=e, countdown=10, max_retries=5)
    else:
        template.set_status("Template preparation finished.")


@shared_task(bind=True)
def prepare_template_delete_on_error(self, template_id):
    try:
        template = Template.objects.get(id=template_id)
    except ObjectDoesNotExist:
        return True
    template.set_status("Template creation failed. Deleting it.")
    try:
        if template.is_created:
            template.provider_api.delete_vm(template.name)
        template.delete()
    except Exception as e:
        self.retry(args=(template_id,), exc=e, countdown=10, max_retries=5)


@shared_task
def request_appliance_pool(appliance_pool_id, time_minutes):
    """This task gives maximum possible amount of spinned-up appliances to the specified pool and
    then if there is need to spin up another appliances, it spins them up via clone_template_to_pool
    task."""
    pool = AppliancePool.objects.get(id=appliance_pool_id)
    n = Appliance.give_to_pool(pool, time_minutes)
    for i in range(pool.total_count - n):
        template_id = random.choice(pool.possible_templates).id
        clone_template_to_pool.delay(template_id, pool.id, time_minutes)


@shared_task
def clone_template_to_pool(template_id, appliance_pool_id, time_minutes):
    template = Template.objects.get(id=template_id)
    pool = AppliancePool.objects.get(id=appliance_pool_id)
    new_appliance_name = settings.APPLIANCE_FORMAT.format(
        group=template.template_group.id,
        date=template.date.strftime("%y%m%d"),
        rnd=generate_random_string())
    appliance = Appliance(template=template, name=new_appliance_name, appliance_pool=pool)
    appliance.save()
    clone_template_to_appliance.delay(appliance.id, time_minutes),


@shared_task
def apply_lease_times(appliance_id, time_minutes):
    with transaction.atomic():
        appliance = Appliance.objects.get(id=appliance_id)
        appliance.datetime_leased = timezone.now()
        appliance.leased_until = appliance.datetime_leased + timedelta(minutes=time_minutes)
        appliance.save()


@shared_task
def clone_template(template_id):
    template = Template.objects.get(id=template_id)
    new_appliance_name = settings.APPLIANCE_FORMAT.format(
        group=template.template_group.id,
        date=template.date.strftime("%y%m%d"),
        rnd=generate_random_string())
    appliance = Appliance(template=template, name=new_appliance_name)
    appliance.save()
    clone_template_to_appliance.delay(appliance.id)


@shared_task
def clone_template_to_appliance(appliance_id, lease_time_minutes=None):
    Appliance.objects.get(id=appliance_id).set_status("Beginning deployment process")
    tasks = [
        clone_template_to_appliance__clone_template.si(appliance_id),
        clone_template_to_appliance__wait_present.si(appliance_id),
        appliance_power_on.si(appliance_id),
        wait_appliance_ready.si(appliance_id),
    ]
    if lease_time_minutes is not None:
        tasks.append(apply_lease_times.si(appliance_id, lease_time_minutes),)
    workflow = chain(*tasks)
    if Appliance.objects.get(id=appliance_id).appliance_pool is not None:
        # Case of the appliance pool
        workflow.link_error(
            kill_appliance.si(appliance_id, replace_in_pool=True, minutes=lease_time_minutes))
    else:
        # Case of shepherd
        workflow.link_error(kill_appliance.si(appliance_id))
    workflow()


@shared_task(bind=True)
def clone_template_to_appliance__clone_template(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        # source objects are not present, terminating the chain
        self.request.callbacks[:] = []
        return
    try:
        if not appliance.provider_api.does_vm_exist(appliance.name):
            appliance.set_status("Beginning template clone.")
            appliance.provider_api.clone_vm(
                appliance.template.name, appliance.name,
                sparse=True, power_on=False, provision_timeout=30 * 60)
    except Exception as e:
        appliance.set_status("Error during template clone ({}).".format(str(e)))
        self.retry(args=(appliance_id,), exc=e, countdown=10, max_retries=5)
    else:
        appliance.set_status("Template cloning finished.")


@shared_task(bind=True)
def clone_template_to_appliance__wait_present(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        # source objects are not present, terminating the chain
        self.request.callbacks[:] = []
        return
    try:
        appliance.set_status("Waiting for the appliance to become visible in provider.")
        if not appliance.provider_api.does_vm_exist(appliance.name):
            self.retry(args=(appliance_id,), countdown=20, max_retries=30)
    except Exception as e:
        self.retry(args=(appliance_id,), exc=e, countdown=20, max_retries=30)
    else:
        appliance.set_status("Template was successfully cloned.")


@shared_task(bind=True)
def appliance_power_on(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        # source objects are not present
        return
    try:
        if appliance.provider_api.is_vm_running(appliance.name):
            retrieve_appliance_ip.delay(appliance_id)  # retrieve IP after power on
            Appliance.objects.get(id=appliance_id).set_status("Appliance was powered on.")
            with transaction.atomic():
                appliance = Appliance.objects.get(id=appliance_id)
                appliance.power_state = Appliance.Power.ON
                appliance.save()
            return
        elif not appliance.provider_api.in_steady_state(appliance.name):
            appliance.set_status("Waiting for appliance to be steady (current state: {}).".format(
                appliance.provider_api.vm_status(appliance.name)))
            self.retry(args=(appliance_id,), countdown=20, max_retries=30)
        else:
            appliance.set_status("Powering on.")
            appliance.provider_api.start_vm(appliance.name)
            self.retry(args=(appliance_id,), countdown=20, max_retries=30)
    except Exception as e:
        self.retry(args=(appliance_id,), exc=e, countdown=20, max_retries=30)


@shared_task(bind=True)
def appliance_power_off(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        # source objects are not present
        return
    try:
        if appliance.provider_api.is_vm_stopped(appliance.name):
            Appliance.objects.get(id=appliance_id).set_status("Appliance was powered off.")
            with transaction.atomic():
                appliance = Appliance.objects.get(id=appliance_id)
                appliance.power_state = Appliance.Power.OFF
                appliance.save()
            return
        elif appliance.provider_api.is_vm_suspended(appliance.name):
            appliance.set_status("Starting appliance from suspended state to properly off it.")
            appliance.provider_api.start_vm(appliance.name)
            self.retry(args=(appliance_id,), countdown=20, max_retries=40)
        elif not appliance.provider_api.in_steady_state(appliance.name):
            appliance.set_status("Waiting for appliance to be steady (current state: {}).".format(
                appliance.provider_api.vm_status(appliance.name)))
            self.retry(args=(appliance_id,), countdown=20, max_retries=40)
        else:
            appliance.set_status("Powering off.")
            appliance.provider_api.stop_vm(appliance.name)
            self.retry(args=(appliance_id,), countdown=20, max_retries=40)
    except Exception as e:
        self.retry(args=(appliance_id,), exc=e, countdown=20, max_retries=40)


@shared_task(bind=True)
def appliance_suspend(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        # source objects are not present
        return
    try:
        if appliance.provider_api.is_vm_suspended(appliance.name):
            Appliance.objects.get(id=appliance_id).set_status("Appliance was suspended.")
            with transaction.atomic():
                appliance = Appliance.objects.get(id=appliance_id)
                appliance.power_state = Appliance.Power.SUSPENDED
                appliance.save()
            return
        elif not appliance.provider_api.in_steady_state(appliance.name):
            appliance.set_status("Waiting for appliance to be steady (current state: {}).".format(
                appliance.provider_api.vm_status(appliance.name)))
            self.retry(args=(appliance_id,), countdown=20, max_retries=30)
        else:
            appliance.set_status("Suspendind.")
            appliance.provider_api.suspend_vm(appliance.name)
            self.retry(args=(appliance_id,), countdown=20, max_retries=30)
    except Exception as e:
        self.retry(args=(appliance_id,), exc=e, countdown=20, max_retries=30)


@shared_task(bind=True)
def retrieve_appliance_ip(self, appliance_id):
    """Updates appliance's IP address."""
    try:
        appliance = Appliance.objects.get(id=appliance_id)
        appliance.set_status("Retrieving IP address.")
        ip_address = appliance.provider_api.current_ip_address(appliance.name)
        if ip_address is None:
            self.retry(args=(appliance_id,), countdown=30, max_retries=20)
        with transaction.atomic():
            appliance = Appliance.objects.get(id=appliance_id)
            appliance.ip_address = ip_address
            appliance.save()
    except ObjectDoesNotExist:
        # source object is not present, terminating
        return
    else:
        appliance.set_status("IP address retrieved.")


@shared_task(bind=True)
def retrieve_appliances_power_states(self):
    """Continuously loops over all appliances and retrieves power states. After the execution ends,
    it schedules itself for execution again after some time"""
    try:
        for a in Appliance.objects.all():
            a.retrieve_power_state()
    finally:
        self.apply_async(countdown=25)


@shared_task(bind=True)
def retrieve_template_existence(self):
    """Continuously loops over all templates and checks whether they are still present in EMS."""
    try:
        for template in Template.objects.all():
            e = template.exists_in_provider
            with transaction.atomic():
                tpl = Template.objects.get(pk=template.pk)
                tpl.exists = e
                tpl.save()
            if not e:
                if len(Appliance.objects.filter(template=template).all()) == 0:
                    # No other appliance is made from this template so no need to keep it
                    with transaction.atomic():
                        tpl = Template.objects.get(pk=template.pk)
                        tpl.delete()
    finally:
        self.apply_async(countdown=600)


@shared_task(bind=True)
def delete_nonexistent_appliances(self):
    """Goes through orphaned appliances' objects and deletes them from the database."""
    try:
        for appliance in Appliance.objects.filter(ready=True).all():
            if appliance.power_state == Appliance.Power.ORPHANED:
                try:
                    appliance.delete()
                except ObjectDoesNotExist as e:
                    if "AppliancePool" in str(e):
                        # Someone managed to delete the appliance pool before
                        appliance.appliance_pool = None
                        appliance.save()
                        appliance.delete()
                    else:
                        raise  # No diaper pattern here!
        # If something happened to the appliance provisioning process, just delete it to remove
        # the garbage. It will be respinned again by shepherd.
        # Grace time is specified in BROKEN_APPLIANCE_GRACE_TIME
        expiration_time = (timezone.now() - timedelta(**settings.BROKEN_APPLIANCE_GRACE_TIME))
        for appliance in Appliance.objects.filter(ready=False, marked_for_deletion=False).all():
            if appliance.status_changed < expiration_time:
                Appliance.kill(appliance)  # Use kill because the appliance may still exist
        # And now - if something happened during appliance deletion, call kill again
        for appliance in Appliance.objects.filter(
                marked_for_deletion=True, status_changed__lt=expiration_time).all():
            with transaction.atomic():
                appl = Appliance.objects.get(pk=appliance.pk)
                appl.marked_for_deletion = False
                appl.save()
            Appliance.kill(appl)
    finally:
        self.apply_async(countdown=120)


@shared_task(bind=True)
def free_appliance_shepherd(self):
    """This task takes care of having the required templates spinned into required number of
    appliances. For each template group, it keeps the last template's appliances spinned up in
    required quantity. If new template comes out of the door, it automatically kills the older
    running template's appliances and spins up new ones."""
    try:
        for grp in Group.objects.all():
            group_versions = Template.get_versions(template_group=grp)
            group_dates = Template.get_dates(template_group=grp)
            if group_versions:
                # Downstream - by version (downstream releases)
                filter_keep = {"version": group_versions[0]}
                filters_kill = [{"version": v} for v in group_versions[1:]]
            elif group_dates:
                # Upstream - by date (upstream nightlies)
                filter_keep = {"date": group_dates[0]}
                filters_kill = [{"date": v} for v in group_dates[1:]]
            else:
                continue  # Ignore this group, no templates detected yet

            # Keeping current appliances
            # Retrieve list of all templates for given group
            # I know joins might be a bit better solution but I'll leave that for later.
            possible_templates = list(
                Template.objects.filter(ready=True, template_group=grp, **filter_keep).all())
            # If it can be deployed, it must exist
            possible_templates_for_provision = filter(lambda tpl: tpl.exists, possible_templates)
            appliances = []
            for template in possible_templates:
                appliances.extend(
                    Appliance.objects.filter(template=template, appliance_pool=None))
            # If we then want to delete some templates, better kill the eldest. status_changed
            # says which one was provisioned when, because nothing else then touches that field.
            appliances.sort(key=lambda appliance: appliance.status_changed)
            if len(appliances) < grp.template_pool_size and possible_templates_for_provision:
                # There must be some templates in order to run the provisioning
                for i in range(grp.template_pool_size - len(appliances)):
                    new_appliance_name = settings.APPLIANCE_FORMAT.format(
                        group=template.template_group.id,
                        date=template.date.strftime("%y%m%d"),
                        rnd=generate_random_string())
                    # We choose random template to spread the load across providers evenly.
                    with transaction.atomic():
                        # Now look for templates that are on non-busy providers
                        tpl_free = filter(
                            lambda t: t.provider.free,
                            possible_templates_for_provision)
                        if not tpl_free:
                            # Bad luck this time, provisioning process is already full. Next time.
                            break
                        appliance = Appliance(
                            template=random.choice(tpl_free),
                            name=new_appliance_name)
                        appliance.save()
                    clone_template_to_appliance.delay(appliance.id)
            elif len(appliances) > grp.template_pool_size:
                # Too many appliances, kill the surplus
                for appliance in appliances[:len(appliances) - grp.template_pool_size]:
                    Appliance.kill(appliance)

            # Killing old appliances
            for filter_kill in filters_kill:
                for template in Template.objects.filter(
                        ready=True, template_group=grp, **filter_kill):
                    for a in Appliance.objects.filter(
                            template=template, appliance_pool=None, marked_for_deletion=False):
                        Appliance.kill(a)
    finally:
        self.apply_async(countdown=60)


@shared_task(bind=True)
def wait_appliance_ready(self, appliance_id):
    """This task checks for appliance's readiness for use. The checking loop is designed as retrying
    the task to free up the queue."""
    try:
        appliance = Appliance.objects.get(id=appliance_id)
        if appliance.power_state == "unknown" or appliance.ip_address is None:
            self.retry(args=(appliance_id,), countdown=60, max_retries=15)
        if Appliance.objects.get(id=appliance_id).cfme.ipapp.is_web_ui_running():
            with transaction.atomic():
                appliance = Appliance.objects.get(id=appliance_id)
                appliance.ready = True
                appliance.save()
            appliance.set_status("The appliance is ready.")
        else:
            with transaction.atomic():
                appliance = Appliance.objects.get(id=appliance_id)
                appliance.ready = False
                appliance.save()
            appliance.set_status("Waiting for UI to appear.")
            self.retry(args=(appliance_id,), countdown=60, max_retries=15)
    except ObjectDoesNotExist:
        # source object is not present, terminating
        return
