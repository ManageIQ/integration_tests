# -*- coding: utf-8 -*-
from __future__ import absolute_import

import hashlib
import random
import re
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone
from celery import chain, chord, shared_task
from datetime import timedelta
from functools import wraps
from novaclient.exceptions import OverLimit as OSOverLimit
from Runner import Run

from appliances.models import (
    Provider, Group, Template, Appliance, AppliancePool, DelayedProvisionTask)
from sprout import settings, redis

from utils.appliance import Appliance as CFMEAppliance
from utils.log import create_logger
from utils.path import project_path
from utils.providers import provider_factory
from utils.randomness import generate_random_string
from utils.trackerbot import api, parse_template


LOCK_EXPIRE = 60 * 15  # 15 minutes
VERSION_REGEXPS = [
    # 4 digits
    r"cfme-(\d)(\d)(\d)(\d)-",      # cfme-5242-    -> 5.2.4.2
    r"cfme-(\d)(\d)(\d)-(\d)-",     # cfme-520-1-   -> 5.2.0.1
    # 5 digits  (not very intelligent but no better solution so far)
    r"cfme-(\d)(\d)(\d)(\d{2})-",   # cfme-53111-   -> 5.3.1.11, cfme-53101 -> 5.3.1.1
]
VERSION_REGEXPS = map(re.compile, VERSION_REGEXPS)


def retrieve_cfme_appliance_version(template_name):
    """If possible, retrieve the appliance's version from template's name."""
    for regexp in VERSION_REGEXPS:
        match = regexp.search(template_name)
        if match is not None:
            return ".".join(map(str, map(int, match.groups())))


def trackerbot():
    return api()


def none_dict(l):
    """"If the parameter passed is None, returns empty dict. Otherwise it passes through"""
    if l is None:
        return {}
    else:
        return l


def logger():
    return create_logger("sprout")


def provider_error_logger():
    return create_logger("provider_error_sprout")


def logged_task(*args, **kwargs):
    def f(task):
        @wraps(task)
        def wrapped_task(*args, **kwargs):
            logger().info(
                "[TASK {}] Entering with arguments: {} / {}".format(
                    task.__name__, ", ".join(map(str, args)), str(kwargs)))
            try:
                return task(*args, **kwargs)
            finally:
                logger().info("[TASK {}] Leaving".format(task.__name__))
        return shared_task(*args, **kwargs)(wrapped_task)
    return f


def singleton_task(*args, **kwargs):
    kwargs["bind"] = True

    def f(task):
        @wraps(task)
        def wrapped_task(self, *args, **kwargs):
            # Create hash of all args
            digest_base = "/".join(str(arg) for arg in args)
            keys = sorted(kwargs.keys())
            digest_base += "//" + "/".join("{}={}".format(key, kwargs[key]) for key in keys)
            digest = hashlib.sha256(digest_base).hexdigest()
            lock_id = '{0}-lock-{1}'.format(self.name, digest)

            if cache.add(lock_id, 'true', LOCK_EXPIRE):
                logger().info(
                    "[SINGLETON TASK {}] Entering with arguments: {} / {}".format(
                        self.name, ", ".join(map(str, args)), str(kwargs)))
                try:
                    return task(self, *args, **kwargs)
                finally:
                    cache.delete(lock_id)
                    logger().info("[SINGLETON TASK {}] Leaving".format(self.name))
            else:
                logger().info("Task {} is already running, ignoring.".format(self.name))

        return shared_task(*args, **kwargs)(wrapped_task)
    return f


@singleton_task()
def poke_providers(self):
    """Basic tasks that checks whether to connections to providers work."""
    for provider in Provider.objects.all():
        poke_provider.delay(provider.id)


@singleton_task(soft_time_limit=60)
def poke_provider(self, provider_id):
    provider = Provider.objects.get(id=provider_id)
    try:
        provider.api
    except:
        provider.working = False
    else:
        provider.working = True
    finally:
        provider.save()


@singleton_task()
def kill_unused_appliances(self):
    """This is the watchdog, that guards the appliances that were given to users. If you forget
    to prolong the lease time, this is the thing that will take the appliance off your hands
    and kill it."""
    with transaction.atomic():
        for appliance in Appliance.objects.filter(marked_for_deletion=False, ready=True):
            if appliance.leased_until is not None and appliance.leased_until <= timezone.now():
                kill_appliance.delay(appliance.id)


@singleton_task()
def kill_appliance(self, appliance_id, replace_in_pool=False, minutes=60):
    """As-reliable-as-possible appliance deleter. Turns off, deletes the VM and deletes the object.

    If the appliance was assigned to pool and we want to replace it, redo the provisioning.
    """
    logger().info("Initiated kill of appliance {}".format(appliance_id))
    workflow = [
        appliance_power_off.si(appliance_id),
        kill_appliance_delete.si(appliance_id),
    ]
    if replace_in_pool:
        appliance = Appliance.objects.get(id=appliance_id)
        if appliance.appliance_pool is not None:
            workflow.append(
                replace_clone_to_pool.si(
                    appliance.template.version, appliance.template.date,
                    appliance.appliance_pool.id, minutes, appliance.template.id))
    workflow = chain(*workflow)
    workflow()


@logged_task(bind=True)
def kill_appliance_delete(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
        if appliance.provider_api.does_vm_exist(appliance.name):
            appliance.set_status("Deleting the appliance from provider")
            appliance.provider_api.delete_vm(appliance.name)
        appliance.delete()
    except ObjectDoesNotExist:
        # Appliance object already not there
        return
    except Exception as e:
        try:
            appliance.set_status("Could not delete appliance. Retrying.")
        except UnboundLocalError:
            return  # The appliance is not there any more
        self.retry(args=(appliance_id,), exc=e, countdown=10, max_retries=5)


@singleton_task()
def poke_trackerbot(self):
    """This beat-scheduled task periodically polls the trackerbot if there are any new templates.
    """
    template_usability = []
    for template in trackerbot().providertemplate().get(limit=10000)["objects"]:
        template_usability.append(
            (
                template["provider"]["key"],
                template["template"]["name"],
                template["usable"]
            )
        )
        if not template["usable"]:
            continue
        group, create = Group.objects.get_or_create(id=template["template"]["group"]["name"])
        provider, create = Provider.objects.get_or_create(id=template["provider"]["key"])
        if not provider.working:
            continue
        if "sprout" not in provider.provider_data:
            continue
        if not provider.provider_data.get("use_for_sprout", False):
            continue
        template_name = template["template"]["name"]
        try:
            Template.objects.get(
                provider=provider, template_group=group, original_name=template_name)
        except ObjectDoesNotExist:
            if template_name in provider.templates:
                create_appliance_template.delay(provider.id, group.id, template_name)
    # If any of the templates becomes unusable, let sprout know about it
    # Similarly if some of them becomes usable ...
    for provider_id, template_name, usability in template_usability:
        provider, create = Provider.objects.get_or_create(id=provider_id)
        try:
            with transaction.atomic():
                template = Template.objects.get(provider=provider, original_name=template_name)
                template.usable = usability
                template.save()
                # Kill all shepherd appliances if they were acidentally spun up
                if not usability:
                    for appliance in Appliance.objects.filter(
                            template=template, ready=True, marked_for_deletion=False,
                            appliance_pool=None):
                        Appliance.kill(appliance)
        except ObjectDoesNotExist:
            pass


@logged_task()
def create_appliance_template(provider_id, group_id, template_name):
    """This task creates a template from a fresh CFME template. In case of fatal error during the
    operation, the template object is deleted to make sure the operation will be retried next time
    when poke_trackerbot runs."""
    provider = Provider.objects.get(id=provider_id)
    provider.cleanup()  # Precaution
    group = Group.objects.get(id=group_id)
    with transaction.atomic():
        # Limit the number of concurrent template configurations
        if provider.remaining_configuring_slots == 0:
            return False  # It will be kicked again when trackerbot gets poked
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
        if provider.template_name_length is not None:
            allowed_length = provider.template_name_length
            # There is some limit
            if len(new_template_name) > allowed_length:
                # Cut it down
                randoms_length = len(new_template_name.rsplit("_", 1)[-1])
                minimum_length = (len(new_template_name) - randoms_length) + 1  # One random must be
                if minimum_length <= allowed_length:
                    # Just cut it
                    new_template_name = new_template_name[:allowed_length]
                else:
                    # Another solution
                    new_template_name = settings.TEMPLATE_FORMAT.format(
                        group=group.id[:2], date=date.strftime("%y%m%d"),  # Use only first 2 of grp
                        rnd=generate_random_string(2))  # And just 2 chars random
                    # TODO: If anything larger comes, do fix that!
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


@logged_task(bind=True)
def prepare_template_deploy(self, template_id):
    template = Template.objects.get(id=template_id)
    try:
        if not template.exists_in_provider:
            template.set_status("Deploying the template.")
            kwargs = template.provider.provider_data["sprout"]
            kwargs["power_on"] = True
            logger().info("Deployment kwargs: {}".format(repr(kwargs)))
            template.provider_api.deploy_template(
                template.original_name, vm_name=template.name, **kwargs)
        else:
            template.set_status("Waiting for deployment to be finished.")
            template.provider_api.wait_vm_running(template.name)
    except Exception as e:
        template.set_status("Could not properly deploy the template. Retrying.")
        self.retry(args=(template_id,), exc=e, countdown=10, max_retries=5)
    else:
        template.set_status("Template deployed.")


@logged_task(bind=True)
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


@logged_task(bind=True)
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


@logged_task(bind=True)
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


@logged_task(bind=True)
def prepare_template_finish(self, template_id):
    template = Template.objects.get(id=template_id)
    template.set_status("Finishing template creation.")
    try:
        if template.temporary_name is None:
            tmp_name = "templatize_{}".format(generate_random_string())
            Template.objects.get(id=template_id).temporary_name = tmp_name
        else:
            tmp_name = template.temporary_name
        template.provider_api.mark_as_template(
            template.name, temporary_name=tmp_name, delete_on_error=False)
        with transaction.atomic():
            template = Template.objects.get(id=template_id)
            template.ready = True
            template.exists = True
            template.save()
            del template.temporary_name
    except Exception as e:
        template.set_status("Could not mark the appliance as template. Retrying.")
        self.retry(args=(template_id,), exc=e, countdown=10, max_retries=5)
    else:
        template.set_status("Template preparation finished.")


@logged_task(bind=True)
def prepare_template_delete_on_error(self, template_id):
    try:
        template = Template.objects.get(id=template_id)
    except ObjectDoesNotExist:
        return True
    template.set_status("Template creation failed. Deleting it.")
    try:
        if template.provider_api.does_vm_exist(template.name):
            template.provider_api.delete_vm(template.name)
        if template.provider_api.does_template_exist(template.name):
            template.provider_api.delete_template(template.name)
        if (template.temporary_name is not None and
                template.provider_api.does_template_exist(template.temporary_name)):
            template.provider_api.delete_template(template.temporary_name)
        template.delete()
    except Exception as e:
        self.retry(args=(template_id,), exc=e, countdown=10, max_retries=5)


@logged_task()
def request_appliance_pool(appliance_pool_id, time_minutes):
    """This task gives maximum possible amount of spinned-up appliances to the specified pool and
    then if there is need to spin up another appliances, it spins them up via clone_template_to_pool
    task."""
    logger().info(
        "Appliance pool {} requested for {} minutes.".format(appliance_pool_id, time_minutes))
    pool = AppliancePool.objects.get(id=appliance_pool_id)
    n = Appliance.give_to_pool(pool)
    for i in range(pool.total_count - n):
        tpls = pool.possible_provisioning_templates
        if tpls:
            template_id = tpls[0].id
            clone_template_to_pool(template_id, pool.id, time_minutes)
        else:
            with transaction.atomic():
                task = DelayedProvisionTask(pool=pool, lease_time=time_minutes)
                task.save()
    apply_lease_times_after_pool_fulfilled.delay(appliance_pool_id, time_minutes)


@logged_task(bind=True)
def apply_lease_times_after_pool_fulfilled(self, appliance_pool_id, time_minutes):
    pool = AppliancePool.objects.get(id=appliance_pool_id)
    if pool.fulfilled:
        for appliance in pool.appliances:
            apply_lease_times.delay(appliance.id, time_minutes)
        # pool_appliances_prefix_with_owner.delay(pool.id)
    else:
        self.retry(args=(appliance_pool_id, time_minutes), countdown=30, max_retries=50)


@singleton_task()
def process_delayed_provision_tasks(self):
    """This picks up the provisioning tasks that were delayed due to ocncurrency limit of provision.

    Goes one task by one and when some of them can be provisioned, it starts the provisioning and
    then deletes the task.
    """
    for task in DelayedProvisionTask.objects.all():
        tpls = task.pool.possible_provisioning_templates
        if task.provider_to_avoid is not None:
            filtered_tpls = filter(lambda tpl: tpl.provider != task.provider_to_avoid, tpls)
            if filtered_tpls:
                # There are other providers to provision on, so try one of them
                tpls = filtered_tpls
            # If there is no other provider to provision on, we will use the original list.
            # This will cause additional rejects until the provider quota is met
        if tpls:
            clone_template_to_pool(tpls[0].id, task.pool.id, task.lease_time)
            task.delete()


@logged_task()
def replace_clone_to_pool(
        version, date, appliance_pool_id, time_minutes, exclude_template_id):
    appliance_pool = AppliancePool.objects.get(id=appliance_pool_id)
    exclude_template = Template.objects.get(id=exclude_template_id)
    templates = Template.objects.filter(
        ready=True, exists=True, usable=True, template_group=appliance_pool.group, version=version,
        date=date).all()
    templates_excluded = filter(lambda tpl: tpl != exclude_template, templates)
    if templates_excluded:
        template = random.choice(templates_excluded)
    else:
        template = exclude_template  # :( no other template to use
    clone_template_to_pool(template.id, appliance_pool_id, time_minutes)


def clone_template_to_pool(template_id, appliance_pool_id, time_minutes):
    template = Template.objects.get(id=template_id)
    new_appliance_name = settings.APPLIANCE_FORMAT.format(
        group=template.template_group.id,
        date=template.date.strftime("%y%m%d"),
        rnd=generate_random_string())
    with transaction.atomic():
        pool = AppliancePool.objects.get(id=appliance_pool_id)
        # Apply also username
        new_appliance_name = "{}_{}".format(pool.owner.username, new_appliance_name)
        appliance = Appliance(template=template, name=new_appliance_name, appliance_pool=pool)
        appliance.save()
        # Set pool to these params to keep the appliances with same versions/dates
        pool.version = template.version
        pool.date = template.date
        pool.save()
    clone_template_to_appliance.delay(appliance.id, time_minutes)


@logged_task()
def apply_lease_times(appliance_id, time_minutes):
    logger().info(
        "Applying lease time {} minutes on appliance {}".format(time_minutes, appliance_id))
    with transaction.atomic():
        appliance = Appliance.objects.get(id=appliance_id)
        appliance.datetime_leased = timezone.now()
        appliance.leased_until = appliance.datetime_leased + timedelta(minutes=time_minutes)
        appliance.save()


@logged_task()
def clone_template(template_id):
    logger().info("Cloning template {}".format(template_id))
    template = Template.objects.get(id=template_id)
    new_appliance_name = settings.APPLIANCE_FORMAT.format(
        group=template.template_group.id,
        date=template.date.strftime("%y%m%d"),
        rnd=generate_random_string())
    appliance = Appliance(template=template, name=new_appliance_name)
    appliance.save()
    clone_template_to_appliance.delay(appliance.id)


@logged_task()
def clone_template_to_appliance(appliance_id, lease_time_minutes=None):
    Appliance.objects.get(id=appliance_id).set_status("Beginning deployment process")
    tasks = [
        clone_template_to_appliance__clone_template.si(appliance_id, lease_time_minutes),
        clone_template_to_appliance__wait_present.si(appliance_id),
        appliance_power_on.si(appliance_id),
    ]
    workflow = chain(*tasks)
    if Appliance.objects.get(id=appliance_id).appliance_pool is not None:
        # Case of the appliance pool
        workflow.link_error(
            kill_appliance.si(appliance_id, replace_in_pool=True, minutes=lease_time_minutes))
    else:
        # Case of shepherd
        workflow.link_error(kill_appliance.si(appliance_id))
    workflow()


@logged_task(bind=True)
def clone_template_to_appliance__clone_template(self, appliance_id, lease_time_minutes):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        # source objects are not present, terminating the chain
        self.request.callbacks[:] = []
        return
    appliance.provider.cleanup()
    try:
        if not appliance.provider_api.does_vm_exist(appliance.name):
            appliance.set_status("Beginning template clone.")
            kwargs = appliance.template.provider.provider_data["sprout"]
            kwargs["power_on"] = False
            logger().info("Deployment kwargs: {}".format(repr(kwargs)))
            appliance.provider_api.deploy_template(
                appliance.template.name, vm_name=appliance.name,
                progress_callback=lambda progress: appliance.set_status(
                    "Deploy progress: {}".format(progress)),
                **kwargs)
    except Exception as e:
        messages = {"limit", "cannot add", "quota"}
        if isinstance(e, OSOverLimit):
            appliance.set_status("Hit OpenStack provisioning quota, trying putting it aside ...")
        elif any(message in str(e).lower() for message in messages):
            appliance.set_status("Provider has some troubles, putting it aside ... {}/{}".format(
                type(e).__name__, str(e)
            ))
            provider_error_logger().exception(e)
        else:
            # Something got screwed really bad
            appliance.set_status("Error happened: {}({})".format(type(e).__name__, str(e)))
            self.retry(args=(appliance_id,), exc=e, countdown=60, max_retries=5)

        # Ignore that and provision it somewhere else
        if appliance.appliance_pool:
            # We can put it aside for a while to wait for
            self.request.callbacks[:] = []  # Quit this chain
            pool = appliance.appliance_pool
            try:
                if appliance.provider_api.does_vm_exist(appliance.name):
                    # Better to check it, you never know when does that fail
                    appliance.provider_api.delete_vm(appliance.name)
            except:
                pass  # Diaper here
            appliance.delete(do_not_touch_ap=True)
            with transaction.atomic():
                new_task = DelayedProvisionTask(
                    pool=pool, lease_time=lease_time_minutes,
                    provider_to_avoid=appliance.template.provider)
                new_task.save()
            return
        else:
            # We cannot put it aside, so just try that again
            self.retry(args=(appliance_id,), exc=e, countdown=60, max_retries=5)
    else:
        appliance.set_status("Template cloning finished.")


@logged_task(bind=True)
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
        provider_error_logger().error("Exception {}: {}".format(type(e).__name__, str(e)))
        self.retry(args=(appliance_id,), exc=e, countdown=20, max_retries=30)
    else:
        appliance.set_status("Template was successfully cloned.")


@singleton_task()
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
                appliance.set_power_state(Appliance.Power.ON)
                appliance.save()
            wait_appliance_ready.delay(appliance.id)
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
        provider_error_logger().error("Exception {}: {}".format(type(e).__name__, str(e)))
        self.retry(args=(appliance_id,), exc=e, countdown=20, max_retries=30)


@singleton_task()
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
                appliance.set_power_state(Appliance.Power.OFF)
                appliance.ready = False
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
        if appliance.provider_api.is_vm_suspended(appliance.name):
            Appliance.objects.get(id=appliance_id).set_status("Appliance was suspended.")
            with transaction.atomic():
                appliance = Appliance.objects.get(id=appliance_id)
                appliance.set_power_state(Appliance.Power.SUSPENDED)
                appliance.ready = False
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
        provider_error_logger().error("Exception {}: {}".format(type(e).__name__, str(e)))
        self.retry(args=(appliance_id,), exc=e, countdown=20, max_retries=30)


@singleton_task()
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


@singleton_task()
def refresh_appliances(self):
    """Dispatches the appliance refresh process among the providers"""
    for provider in Provider.objects.all():
        refresh_appliances_provider.delay(provider.id)


@singleton_task(soft_time_limit=180)
def refresh_appliances_provider(self, provider_id):
    """Downloads the list of VMs from the provider, then matches them by name or UUID with
    appliances stored in database.
    """
    provider = Provider.objects.get(id=provider_id)
    vms = provider.api.all_vms()
    dict_vms = {}
    uuid_vms = {}
    for vm in vms:
        dict_vms[vm.name] = vm
        uuid_vms[vm.uuid] = vm
    for appliance in Appliance.objects.filter(template__provider=provider):
        if appliance.uuid is not None and appliance.uuid in uuid_vms:
            vm = uuid_vms[appliance.uuid]
            # Using the UUID and change the name if it changed
            appliance.name = vm.name
            appliance.ip_address = vm.ip
            appliance.set_power_state(Appliance.POWER_STATES_MAPPING.get(
                vm.power_state, Appliance.Power.UNKNOWN))
            appliance.save()
        elif appliance.name in dict_vms:
            vm = dict_vms[appliance.name]
            # Using the name, and then retrieve uuid
            appliance.uuid = vm.uuid
            appliance.ip_address = vm.ip
            appliance.set_power_state(Appliance.POWER_STATES_MAPPING.get(
                vm.power_state, Appliance.Power.UNKNOWN))
            appliance.save()
        else:
            # Orphaned :(
            appliance.set_power_state(Appliance.Power.ORPHANED)
            appliance.save()


@singleton_task()
def check_templates(self):
    for provider in Provider.objects.all():
        check_templates_in_provider.delay(provider.id)


@singleton_task(soft_time_limit=180)
def check_templates_in_provider(self, provider_id):
    provider = Provider.objects.get(id=provider_id)
    # Get templates and update metadata
    try:
        templates = map(str, provider.api.list_template())
    except:
        provider.working = False
        provider.save()
    else:
        with provider.edit_metadata as metadata:
            metadata["templates"] = templates
    if not provider.working:
        return
    # Check Sprout template existence
    # expiration_time = (timezone.now() - timedelta(**settings.BROKEN_APPLIANCE_GRACE_TIME))
    for template in Template.objects.filter(provider=provider):
        with transaction.atomic():
            tpl = Template.objects.get(pk=template.pk)
            exists = tpl.name in templates
            tpl.exists = exists
            tpl.save()
        # if not exists:
        #     if len(Appliance.objects.filter(template=template).all()) == 0\
        #             and template.status_changed < expiration_time:
        #         # No other appliance is made from this template so no need to keep it
        #         with transaction.atomic():
        #             tpl = Template.objects.get(pk=template.pk)
        #             tpl.delete()


@singleton_task()
def delete_nonexistent_appliances(self):
    """Goes through orphaned appliances' objects and deletes them from the database."""
    expiration_time = (timezone.now() - timedelta(**settings.ORPHANED_APPLIANCE_GRACE_TIME))
    for appliance in Appliance.objects.filter(ready=True).all():
        if appliance.name in redis.renaming_appliances:
            continue
        if appliance.power_state == Appliance.Power.ORPHANED:
            if appliance.power_state_changed > expiration_time:
                # Ignore it for now
                continue
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


@singleton_task()
def free_appliance_shepherd(self):
    """This task takes care of having the required templates spinned into required number of
    appliances. For each template group, it keeps the last template's appliances spinned up in
    required quantity. If new template comes out of the door, it automatically kills the older
    running template's appliances and spins up new ones."""
    for grp in Group.objects.all():
        group_versions = Template.get_versions(template_group=grp, ready=True, usable=True)
        group_dates = Template.get_dates(template_group=grp, ready=True, usable=True)
        if group_versions:
            # Downstream - by version (downstream releases)
            version = group_versions[0]
            # Find the latest date (one version can have new build)
            dates = Template.get_dates(
                template_group=grp, ready=True, usable=True, version=group_versions[0])
            if not dates:
                # No template yet?
                continue
            date = dates[0]
            filter_keep = {"version": version, "date": date}
            filters_kill = []
            for kill_date in dates[1:]:
                filters_kill.append({"version": version, "date": kill_date})
            for kill_version in group_versions[1:]:
                filters_kill.append({"version": kill_version})
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
            Template.objects.filter(
                usable=True, ready=True, template_group=grp, **filter_keep).all())
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
                    ready=True, usable=True, template_group=grp, **filter_kill):
                for a in Appliance.objects.filter(
                        template=template, appliance_pool=None, marked_for_deletion=False):
                    Appliance.kill(a)


@singleton_task()
def wait_appliance_ready(self, appliance_id):
    """This task checks for appliance's readiness for use. The checking loop is designed as retrying
    the task to free up the queue."""
    try:
        appliance = Appliance.objects.get(id=appliance_id)
        if appliance.power_state == "unknown" or appliance.ip_address is None:
            self.retry(args=(appliance_id,), countdown=20, max_retries=45)
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
            self.retry(args=(appliance_id,), countdown=20, max_retries=45)
    except ObjectDoesNotExist:
        # source object is not present, terminating
        return


@singleton_task()
def anyvm_power_on(self, provider, vm):
    provider = provider_factory(provider)
    provider.start_vm(vm)


@singleton_task()
def anyvm_power_off(self, provider, vm):
    provider = provider_factory(provider)
    provider.stop_vm(vm)


@singleton_task()
def anyvm_suspend(self, provider, vm):
    provider = provider_factory(provider)
    provider.suspend_vm(vm)


@singleton_task()
def anyvm_delete(self, provider, vm):
    provider = provider_factory(provider)
    provider.delete_vm(vm)


@singleton_task()
def delete_template_from_provider(self, template_id):
    template = Template.objects.get(id=template_id)
    template.provider_api.delete_template(template.name)
    with transaction.atomic():
        template = Template.objects.get(pk=template.pk)
        template.exists = False
        template.save()


@logged_task(bind=True)
def appliance_rename(self, appliance_id, new_name):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        return
    if appliance.name == new_name:
        return
    with redis.appliances_ignored_when_renaming(appliance.name, new_name):
        appliance.name = appliance.provider_api.rename_vm(appliance.name, new_name)
        appliance.save()


@logged_task(bind=True)
def pool_appliances_prefix_with_owner(self, pool_id):
    with transaction.atomic():
        try:
            appliance_pool = AppliancePool.objects.get(id=pool_id)
        except ObjectDoesNotExist:
            return
        appliances = [
            appliance
            for appliance
            in appliance_pool.appliances
            if (not appliance.name.startswith(appliance_pool.owner.username))
            and appliance.provider_api.can_rename
        ]
        for appliance in appliances:
            appliance_rename.apply_async(
                countdown=10,  # To prevent clogging with the transaction.atomic
                args=(appliance.id, "{}_{}".format(appliance_pool.owner.username, appliance.name)))


@singleton_task(soft_time_limit=60)
def check_update(self):
    sprout_sh = project_path.join("sprout").join("sprout.sh")
    result = Run.command("{} check-update".format(sprout_sh.strpath))
    needs_update = result.stdout.strip().lower() != "up-to-date"
    redis.set("sprout-needs-update", needs_update)


@singleton_task()
def scavenge_managed_providers(self):
    chord_tasks = []
    for appliance in Appliance.objects.exclude(appliance_pool=None):
        chord_tasks.append(scavenge_managed_providers_from_appliance.si(appliance.id))
    chord(chord_tasks)(calculate_provider_management_usage.s())


@singleton_task(soft_time_limit=180)
def scavenge_managed_providers_from_appliance(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        return None
    try:
        managed_providers = appliance.ipapp.managed_providers
        appliance.managed_providers = managed_providers
    except Exception as e:
        # To prevent single appliance messing up whole result
        provider_error_logger().error("{}: {}".format(type(e).__name__, str(e)))
        return None
    return appliance.id


@singleton_task()
def calculate_provider_management_usage(self, appliance_ids):
    results = {}
    for appliance_id in filter(lambda id: id is not None, appliance_ids):
        appliance = Appliance.objects.get(id=appliance_id)
        for provider in appliance.managed_providers:
            if provider not in results:
                results[provider] = []
            results[provider].append(appliance.id)
    for provider in Provider.objects.all():
        provider.appliances_manage_this_provider = results.get(provider.id, [])
