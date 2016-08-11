# -*- coding: utf-8 -*-
from __future__ import absolute_import

import diaper
import fauxfactory
import hashlib
import iso8601
import random
import re
import command
import yaml
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from celery import chain, chord, shared_task
from celery.exceptions import MaxRetriesExceededError
from datetime import timedelta
from functools import wraps
from novaclient.exceptions import OverLimit as OSOverLimit
from paramiko import SSHException
import socket

from appliances.models import (
    Provider, Group, Template, Appliance, AppliancePool, DelayedProvisionTask,
    MismatchVersionMailer, User)
from sprout import settings, redis
from sprout.irc_bot import send_message
from sprout.log import create_logger

from utils import conf
from utils.appliance import Appliance as CFMEAppliance
from utils.path import project_path
from utils.providers import get_mgmt
from utils.timeutil import parsetime
from utils.trackerbot import api, depaginate, parse_template
from utils.version import Version
from utils.wait import wait_for


LOCK_EXPIRE = 60 * 15  # 15 minutes
VERSION_REGEXPS = [
    r"^cfme-(\d)(\d)(\d)(\d)(\d{2})",  # 1.2.3.4.11
    # newer format
    r"cfme-(\d)(\d)(\d)[.](\d{2})-",         # cfme-524.02-    -> 5.2.4.2
    r"cfme-(\d)(\d)(\d)[.](\d{2})[.](\d)-",  # cfme-524.02.1-    -> 5.2.4.2.1
    # 4 digits
    r"cfme-(?:nightly-)?(\d)(\d)(\d)(\d)-",      # cfme-5242-    -> 5.2.4.2
    r"cfme-(\d)(\d)(\d)-(\d)-",     # cfme-520-1-   -> 5.2.0.1
    # 5 digits  (not very intelligent but no better solution so far)
    r"cfme-(?:nightly-)?(\d)(\d)(\d)(\d{2})-",   # cfme-53111-   -> 5.3.1.11, cfme-53101 -> 5.3.1.1
]
VERSION_REGEXPS = map(re.compile, VERSION_REGEXPS)
TRACKERBOT_PAGINATE = 20


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


def provider_error_logger():
    return create_logger("provider_errors")


def logged_task(*args, **kwargs):
    kwargs["bind"] = True

    def f(task):
        @wraps(task)
        def wrapped_task(self, *args, **kwargs):
            self.logger = create_logger(task)
            self.logger.info(
                "Entering with arguments: {} / {}".format(", ".join(map(str, args)), str(kwargs)))
            try:
                return task(self, *args, **kwargs)
            finally:
                self.logger.info("Leaving")
        return shared_task(*args, **kwargs)(wrapped_task)
    return f


def singleton_task(*args, **kwargs):
    kwargs["bind"] = True
    wait = kwargs.pop('wait', False)
    wait_countdown = kwargs.pop('wait_countdown', 10)
    wait_retries = kwargs.pop('wait_retries', 30)

    def f(task):
        @wraps(task)
        def wrapped_task(self, *args, **kwargs):
            self.logger = create_logger(task)
            # Create hash of all args
            digest_base = "/".join(str(arg) for arg in args)
            keys = sorted(kwargs.keys())
            digest_base += "//" + "/".join("{}={}".format(key, kwargs[key]) for key in keys)
            digest = hashlib.sha256(digest_base).hexdigest()
            lock_id = '{0}-lock-{1}'.format(self.name, digest)

            if cache.add(lock_id, 'true', LOCK_EXPIRE):
                self.logger.info(
                    "Entering with arguments: {} / {}".format(
                        ", ".join(map(str, args)), str(kwargs)))
                try:
                    return task(self, *args, **kwargs)
                finally:
                    cache.delete(lock_id)
                    self.logger.info("Leaving")
            elif wait:
                self.logger.info("Waiting for another instance of the task to end.")
                self.retry(args=args, countdown=wait_countdown, max_retries=wait_retries)
            else:
                self.logger.info("Already running, ignoring.")

        return shared_task(*args, **kwargs)(wrapped_task)
    return f


@singleton_task()
def kill_unused_appliances(self):
    """This is the watchdog, that guards the appliances that were given to users. If you forget
    to prolong the lease time, this is the thing that will take the appliance off your hands
    and kill it."""
    with transaction.atomic():
        for appliance in Appliance.objects.filter(marked_for_deletion=False, ready=True):
            if appliance.leased_until is not None and appliance.leased_until <= timezone.now():
                self.logger.info("Watchdog found an appliance that is to be deleted: {}/{}".format(
                    appliance.id, appliance.name))
                kill_appliance.delay(appliance.id)


@singleton_task()
def kill_appliance(self, appliance_id, replace_in_pool=False, minutes=60):
    """As-reliable-as-possible appliance deleter. Turns off, deletes the VM and deletes the object.

    If the appliance was assigned to pool and we want to replace it, redo the provisioning.
    """
    self.logger.info("Initiated kill of appliance {}".format(appliance_id))
    workflow = [
        disconnect_direct_lun.si(appliance_id),
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


@singleton_task()
def kill_appliance_delete(self, appliance_id, _delete_already_issued=False):
    delete_issued = False
    try:
        appliance = Appliance.objects.get(id=appliance_id)
        if appliance.provider_api.does_vm_exist(appliance.name):
            appliance.set_status("Deleting the appliance from provider")
            # If we haven't issued the delete order, do it now
            if not _delete_already_issued:
                appliance.provider_api.delete_vm(appliance.name)
                delete_issued = True
            # In any case, retry to wait for the VM to be deleted, but next time do not issue delete
            self.retry(args=(appliance_id, True), countdown=5, max_retries=60)
        appliance.delete()
    except ObjectDoesNotExist:
        # Appliance object already not there
        return
    except Exception as e:
        try:
            appliance.set_status("Could not delete appliance. Retrying.")
        except UnboundLocalError:
            return  # The appliance is not there any more
        # In case of error retry, and also specify whether the delete order was already issued
        self.retry(
            args=(appliance_id, _delete_already_issued or delete_issued),
            exc=e, countdown=5, max_retries=60)


@singleton_task()
def poke_trackerbot(self):
    """This beat-scheduled task periodically polls the trackerbot if there are any new templates.
    """
    template_usability = []
    # Extract data from trackerbot
    tbapi = trackerbot()
    objects = depaginate(tbapi, tbapi.providertemplate().get(limit=TRACKERBOT_PAGINATE))["objects"]
    per_group = {}
    for obj in objects:
        if obj["template"]["group"]["name"] not in per_group:
            per_group[obj["template"]["group"]["name"]] = []

        per_group[obj["template"]["group"]["name"]].append(obj)
    # Sort them using the build date
    for group in per_group.iterkeys():
        per_group[group] = sorted(
            per_group[group],
            reverse=True, key=lambda o: o["template"]["datestamp"])
    objects = []
    # And interleave the the groups
    while any(per_group.values()):
        for key in per_group.iterkeys():
            if per_group[key]:
                objects.append(per_group[key].pop(0))
    for template in objects:
        if template["provider"]["key"] not in conf.cfme_data.management_systems.keys():
            # If we don't use that provider in yamls, set the template as not usable
            # 1) It will prevent adding this template if not added
            # 2) It'll mark the template as unusable if it already exists
            template["usable"] = False
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
        # Check if the template is already obsolete
        if group.template_obsolete_days is not None:
            build_date = parsetime.from_iso_date(template["template"]["datestamp"])
            if build_date <= (parsetime.today() - timedelta(days=group.template_obsolete_days)):
                # It is already obsolete, so ignore it
                continue
        provider, create = Provider.objects.get_or_create(id=template["provider"]["key"])
        if not provider.is_working:
            continue
        if "sprout" not in provider.provider_data:
            continue
        if not provider.provider_data.get("use_for_sprout", False):
            continue
        template_name = template["template"]["name"]
        date = parse_template(template_name).datestamp
        if not date:
            # Not a CFME/MIQ template, ignore it.
            continue
        # Original one
        original_template = None
        try:
            original_template = Template.objects.get(
                provider=provider, template_group=group, original_name=template_name,
                name=template_name, preconfigured=False)
        except ObjectDoesNotExist:
            if template_name in provider.templates:
                date = parse_template(template_name).datestamp
                if date is None:
                    self.logger.warning(
                        "Ignoring template {} because it does not have a date!".format(
                            template_name))
                    continue
                template_version = retrieve_cfme_appliance_version(template_name)
                if template_version is None:
                    # Make up a faux version
                    # First 3 fields of version get parsed as a zstream
                    # therefore ... makes it a "nil" stream
                    template_version = "...{}".format(date.strftime("%Y%m%d"))
                with transaction.atomic():
                    tpl = Template(
                        provider=provider, template_group=group, original_name=template_name,
                        name=template_name, preconfigured=False, date=date,
                        version=template_version, ready=True, exists=True, usable=True)
                    tpl.save()
                    original_template = tpl
                    self.logger.info("Created a new template #{}".format(tpl.id))
        # Preconfigured one
        try:
            Template.objects.get(
                provider=provider, template_group=group, original_name=template_name,
                preconfigured=True)
        except ObjectDoesNotExist:
            if template_name in provider.templates:
                original_id = original_template.id if original_template is not None else None
                create_appliance_template.delay(
                    provider.id, group.id, template_name, source_template_id=original_id)
    # If any of the templates becomes unusable, let sprout know about it
    # Similarly if some of them becomes usable ...
    for provider_id, template_name, usability in template_usability:
        provider, create = Provider.objects.get_or_create(id=provider_id)
        with transaction.atomic():
            for template in Template.objects.filter(provider=provider, original_name=template_name):
                template.usable = usability
                template.save()
                # Kill all shepherd appliances if they were acidentally spun up
                if not usability:
                    for appliance in Appliance.objects.filter(
                            template=template, ready=True, marked_for_deletion=False,
                            appliance_pool=None):
                        Appliance.kill(appliance)


@logged_task()
def create_appliance_template(self, provider_id, group_id, template_name, source_template_id=None):
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
                template_group=group, provider=provider, original_name=template_name,
                preconfigured=True)
            return False
        except ObjectDoesNotExist:
            pass
        # Fire off the template preparation
        date = parse_template(template_name).datestamp
        if not date:
            return
        template_version = retrieve_cfme_appliance_version(template_name)
        if template_version is None:
            # Make up a faux version
            # First 3 fields of version get parsed as a zstream
            # therefore ... makes it a "nil" stream
            template_version = "...{}".format(date.strftime("%Y%m%d"))
        new_template_name = settings.TEMPLATE_FORMAT.format(
            group=group.id, date=date.strftime("%y%m%d"), rnd=fauxfactory.gen_alphanumeric(8))
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
                        rnd=fauxfactory.gen_alphanumeric(2))  # And just 2 chars random
                    # TODO: If anything larger comes, do fix that!
        if source_template_id is not None:
            try:
                source_template = Template.objects.get(id=source_template_id)
            except ObjectDoesNotExist:
                source_template = None
        else:
            source_template = None
        template = Template(
            provider=provider, template_group=group, name=new_template_name, date=date,
            version=template_version, original_name=template_name, parent_template=source_template)
        template.save()
    workflow = chain(
        prepare_template_deploy.si(template.id),
        prepare_template_verify_version.si(template.id),
        prepare_template_configure.si(template.id),
        prepare_template_seal.si(template.id),
        prepare_template_poweroff.si(template.id),
        prepare_template_finish.si(template.id),
    )
    workflow.link_error(prepare_template_delete_on_error.si(template.id))
    workflow()


@singleton_task()
def prepare_template_deploy(self, template_id):
    template = Template.objects.get(id=template_id)
    try:
        if not template.exists_in_provider:
            template.set_status("Deploying the template.")
            provider_data = template.provider.provider_data
            kwargs = provider_data["sprout"]
            kwargs["power_on"] = True
            if "allowed_datastores" not in kwargs and "allowed_datastores" in provider_data:
                kwargs["allowed_datastores"] = provider_data["allowed_datastores"]
            self.logger.info("Deployment kwargs: {}".format(repr(kwargs)))
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


@singleton_task()
def prepare_template_verify_version(self, template_id):
    template = Template.objects.get(id=template_id)
    template.set_status("Verifying version.")
    appliance = CFMEAppliance(template.provider_name, template.name)
    appliance.ipapp.wait_for_ssh()
    try:
        true_version = appliance.version
    except Exception as e:
        template.set_status("Some SSH error happened during appliance version check.")
        self.retry(args=(template_id,), exc=e, countdown=20, max_retries=5)
    supposed_version = Version(template.version)
    if true_version is None or true_version.vstring == 'master':
        return
    if true_version != supposed_version:
        # Check if the difference is not just in the suffixes, which can be the case ...
        if supposed_version.version == true_version.version:
            # The two have same version but different suffixes, apply the suffix to the template obj
            with transaction.atomic():
                template.version = str(true_version)
                template.save()
                if template.parent_template is not None:
                    # In case we have a parent template, update the version there too.
                    if template.version != template.parent_template.version:
                        pt = template.parent_template
                        pt.version = template.version
                        pt.save()
            return  # no need to continue with spamming process
        # SPAM SPAM SPAM!
        with transaction.atomic():
            mismatch_in_db = MismatchVersionMailer.objects.filter(
                provider=template.provider,
                template_name=template.original_name,
                supposed_version=supposed_version,
                actual_version=true_version)
            if not mismatch_in_db:
                mismatch = MismatchVersionMailer(
                    provider=template.provider,
                    template_name=template.original_name,
                    supposed_version=supposed_version,
                    actual_version=true_version)
                mismatch.save()
        # Run the task to mail the problem
        mailer_version_mismatch.delay()
        raise Exception("Detected version mismatch!")


@singleton_task()
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


@singleton_task()
def prepare_template_seal(self, template_id):
    template = Template.objects.get(id=template_id)
    template.set_status("Sealing template.")
    try:
        template.cfme.ipapp.seal_for_templatizing()
    except Exception as e:
        template.set_status("Could not seal the template. Retrying.")
        self.retry(
            args=(template_id,), exc=e, countdown=10, max_retries=5)
    else:
        template.set_status("Template sealed.")


@singleton_task()
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


@singleton_task()
def prepare_template_finish(self, template_id):
    template = Template.objects.get(id=template_id)
    template.set_status("Finishing template creation.")
    try:
        if template.temporary_name is None:
            tmp_name = "templatize_{}".format(fauxfactory.gen_alphanumeric(8))
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


@singleton_task()
def prepare_template_delete_on_error(self, template_id):
    try:
        template = Template.objects.get(id=template_id)
    except ObjectDoesNotExist:
        return True
    template.set_status("Template creation failed. Deleting it.")
    try:
        if template.provider_api.does_vm_exist(template.name):
            template.provider_api.delete_vm(template.name)
            wait_for(template.provider_api.does_vm_exist, [template.name], timeout='5m', delay=10)
        if template.provider_api.does_template_exist(template.name):
            template.provider_api.delete_template(template.name)
            wait_for(
                template.provider_api.does_template_exist, [template.name], timeout='5m', delay=10)
        if (template.temporary_name is not None and
                template.provider_api.does_template_exist(template.temporary_name)):
            template.provider_api.delete_template(template.temporary_name)
            wait_for(
                template.provider_api.does_template_exist,
                [template.temporary_name], timeout='5m', delay=10)
        template.delete()
    except Exception as e:
        self.retry(args=(template_id,), exc=e, countdown=10, max_retries=5)


@logged_task()
def request_appliance_pool(self, appliance_pool_id, time_minutes):
    """This task gives maximum possible amount of spinned-up appliances to the specified pool and
    then if there is need to spin up another appliances, it spins them up via clone_template_to_pool
    task."""
    self.logger.info(
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


@singleton_task()
def apply_lease_times_after_pool_fulfilled(self, appliance_pool_id, time_minutes):
    pool = AppliancePool.objects.get(id=appliance_pool_id)
    if pool.fulfilled:
        for appliance in pool.appliances:
            apply_lease_times.delay(appliance.id, time_minutes)
        # TODO: Renaming disabled until orphaning and killing resolved
        # rename_appliances_for_pool.delay(pool.id)
        with transaction.atomic():
            pool.finished = True
            pool.save()
    else:
        # Look whether we can swap any provisioning appliance with some in shepherd
        unfinished = list(Appliance.objects.filter(appliance_pool=pool, ready=False).all())
        random.shuffle(unfinished)
        if len(unfinished) > 0:
            n = Appliance.give_to_pool(pool, len(unfinished))
            with transaction.atomic():
                for _ in range(n):
                    appl = unfinished.pop()
                    appl.appliance_pool = None
                    appl.save()
        try:
            self.retry(args=(appliance_pool_id, time_minutes), countdown=30, max_retries=120)
        except MaxRetriesExceededError:  # Bad luck, pool fulfillment failed. So destroy it.
            pool.logger.error("Waiting for fulfillment failed. Initiating the destruction process.")
            pool.kill()


@singleton_task()
def process_delayed_provision_tasks(self):
    """This picks up the provisioning tasks that were delayed due to ocncurrency limit of provision.

    Goes one task by one and when some of them can be provisioned, it starts the provisioning and
    then deletes the task.
    """
    for task in DelayedProvisionTask.objects.order_by("id"):
        if task.pool.not_needed_anymore:
            task.delete()
            continue
        # Try retrieve from shepherd
        appliances_given = Appliance.give_to_pool(task.pool, 1)
        if appliances_given == 0:
            # No free appliance in shepherd, so do it on our own
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
            else:
                # Try freeing up some space in provider
                for provider in task.pool.possible_providers:
                    appliances = provider.free_shepherd_appliances.exclude(
                        **task.pool.appliance_filter_params)
                    if appliances:
                        Appliance.kill(random.choice(appliances))
                        break  # Just one
        else:
            # There was a free appliance in shepherd, so we took it and we don't need this task more
            task.delete()


@logged_task()
def replace_clone_to_pool(
        self, version, date, appliance_pool_id, time_minutes, exclude_template_id):
    appliance_pool = AppliancePool.objects.get(id=appliance_pool_id)
    if appliance_pool.not_needed_anymore:
        return
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
        rnd=fauxfactory.gen_alphanumeric(8))
    with transaction.atomic():
        pool = AppliancePool.objects.get(id=appliance_pool_id)
        if pool.not_needed_anymore:
            return
        # Apply also username
        new_appliance_name = "{}_{}".format(pool.owner.username, new_appliance_name)
        appliance = Appliance(template=template, name=new_appliance_name, appliance_pool=pool)
        appliance.save()
        # Set pool to these params to keep the appliances with same versions/dates
        pool.version = template.version
        pool.date = template.date
        pool.save()
    clone_template_to_appliance.delay(appliance.id, time_minutes, pool.yum_update)


@logged_task()
def apply_lease_times(self, appliance_id, time_minutes):
    self.logger.info(
        "Applying lease time {} minutes on appliance {}".format(time_minutes, appliance_id))
    with transaction.atomic():
        appliance = Appliance.objects.get(id=appliance_id)
        appliance.datetime_leased = timezone.now()
        appliance.leased_until = appliance.datetime_leased + timedelta(minutes=time_minutes)
        appliance.save()


@logged_task()
def clone_template(self, template_id):
    self.logger.info("Cloning template {}".format(template_id))
    template = Template.objects.get(id=template_id)
    new_appliance_name = settings.APPLIANCE_FORMAT.format(
        group=template.template_group.id,
        date=template.date.strftime("%y%m%d"),
        rnd=fauxfactory.gen_alphanumeric(8))
    appliance = Appliance(template=template, name=new_appliance_name)
    appliance.save()
    clone_template_to_appliance.delay(appliance.id)


@singleton_task()
def clone_template_to_appliance(self, appliance_id, lease_time_minutes=None, yum_update=False):
    appliance = Appliance.objects.get(id=appliance_id)
    appliance.set_status("Beginning deployment process")
    tasks = [
        clone_template_to_appliance__clone_template.si(appliance_id, lease_time_minutes),
        clone_template_to_appliance__wait_present.si(appliance_id),
        appliance_power_on.si(appliance_id),
    ]
    if yum_update:
        tasks.append(appliance_yum_update.si(appliance_id))
        tasks.append(appliance_reboot.si(appliance_id, if_needs_restarting=True))
    if appliance.preconfigured:
        tasks.append(wait_appliance_ready.si(appliance_id))
    else:
        tasks.append(mark_appliance_ready.si(appliance_id))
    workflow = chain(*tasks)
    if Appliance.objects.get(id=appliance_id).appliance_pool is not None:
        # Case of the appliance pool
        if Appliance.objects.get(id=appliance_id).appliance_pool.not_needed_anymore:
            return
        # TODO: Make replace_in_pool work again
        workflow.link_error(
            kill_appliance.si(appliance_id, replace_in_pool=False, minutes=lease_time_minutes))
    else:
        # Case of shepherd
        workflow.link_error(kill_appliance.si(appliance_id))
    workflow()


@singleton_task()
def clone_template_to_appliance__clone_template(self, appliance_id, lease_time_minutes):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        # source objects are not present, terminating the chain
        self.request.callbacks[:] = []
        return
    if appliance.appliance_pool is not None:
        if appliance.appliance_pool.not_needed_anymore:
            # Terminate task chain
            self.request.callbacks[:] = []
            kill_appliance.delay(appliance_id)
            return
    appliance.provider.cleanup()
    try:
        if not appliance.provider_api.does_vm_exist(appliance.name):
            appliance.set_status("Beginning template clone.")
            provider_data = appliance.template.provider.provider_data
            kwargs = provider_data["sprout"]
            kwargs["power_on"] = False
            if "allowed_datastores" not in kwargs and "allowed_datastores" in provider_data:
                kwargs["allowed_datastores"] = provider_data["allowed_datastores"]
            self.logger.info("Deployment kwargs: {}".format(repr(kwargs)))
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
            self.retry(args=(appliance_id, lease_time_minutes), exc=e, countdown=60, max_retries=5)

        # Ignore that and provision it somewhere else
        if appliance.appliance_pool:
            # We can put it aside for a while to wait for
            self.request.callbacks[:] = []  # Quit this chain
            pool = appliance.appliance_pool
            try:
                if appliance.provider_api.does_vm_exist(appliance.name):
                    # Better to check it, you never know when does that fail
                    appliance.provider_api.delete_vm(appliance.name)
                    wait_for(
                        appliance.provider_api.does_vm_exist,
                        [appliance.name], timeout='5m', delay=10)
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
            self.retry(args=(appliance_id, lease_time_minutes), exc=e, countdown=60, max_retries=5)
    else:
        appliance.set_status("Template cloning finished. Refreshing provider VMs to get UUID.")
        refresh_appliances_provider.delay(appliance.provider.id)


@singleton_task()
def clone_template_to_appliance__wait_present(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        # source objects are not present, terminating the chain
        self.request.callbacks[:] = []
        return
    if appliance.appliance_pool is not None:
        if appliance.appliance_pool.not_needed_anymore:
            # Terminate task chain
            self.request.callbacks[:] = []
            kill_appliance.delay(appliance_id)
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
        with diaper:
            appliance.synchronize_metadata()


@singleton_task()
def mark_appliance_ready(self, appliance_id):
    with transaction.atomic():
        appliance = Appliance.objects.get(id=appliance_id)
        appliance.ready = True
        appliance.save()
    Appliance.objects.get(id=appliance_id).set_status("Appliance was marked as ready")


@singleton_task()
def appliance_power_on(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        # source objects are not present
        return
    try:
        if appliance.provider_api.is_vm_running(appliance.name):
            Appliance.objects.get(id=appliance_id).set_status("Appliance was powered on.")
            with transaction.atomic():
                appliance = Appliance.objects.get(id=appliance_id)
                appliance.set_power_state(Appliance.Power.ON)
                appliance.save()
            return
        elif not appliance.provider_api.in_steady_state(appliance.name):
            appliance.set_status("Waiting for appliance to be steady (current state: {}).".format(
                appliance.provider_api.vm_status(appliance.name)))
            self.retry(args=(appliance_id, ), countdown=20, max_retries=40)
        else:
            appliance.set_status("Powering on.")
            appliance.provider_api.start_vm(appliance.name)
            self.retry(args=(appliance_id, ), countdown=20, max_retries=40)
    except Exception as e:
        provider_error_logger().error("Exception {}: {}".format(type(e).__name__, str(e)))
        self.retry(args=(appliance_id, ), exc=e, countdown=20, max_retries=30)


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
        appliance.ipapp.reboot(wait_for_web_ui=False, log_callback=appliance.set_status)
        with transaction.atomic():
            appliance = Appliance.objects.get(id=appliance_id)
            appliance.set_power_state(Appliance.Power.ON)
            appliance.save()
    except Exception as e:
        provider_error_logger().error("Exception {}: {}".format(type(e).__name__, str(e)))
        self.retry(args=(appliance_id, ), exc=e, countdown=20, max_retries=30)


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
            appliance.set_status("Suspending.")
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
    self.logger.info("Initiating regular appliance provider refresh")
    for provider in Provider.objects.filter(working=True, disabled=False):
        refresh_appliances_provider.delay(provider.id)


@singleton_task(soft_time_limit=180)
def refresh_appliances_provider(self, provider_id):
    """Downloads the list of VMs from the provider, then matches them by name or UUID with
    appliances stored in database.
    """
    self.logger.info("Refreshing appliances in {}".format(provider_id))
    provider = Provider.objects.get(id=provider_id)
    if not hasattr(provider.api, "all_vms"):
        # Ignore this provider
        return
    vms = provider.api.all_vms()
    dict_vms = {}
    uuid_vms = {}
    for vm in vms:
        dict_vms[vm.name] = vm
        if vm.uuid:
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
            self.logger.info("Retrieved UUID for appliance {}/{}: {}".format(
                appliance.id, appliance.name, appliance.uuid))
        else:
            # Orphaned :(
            appliance.set_power_state(Appliance.Power.ORPHANED)
            appliance.save()


@singleton_task()
def check_templates(self):
    self.logger.info("Initiated a periodic template check")
    for provider in Provider.objects.all():
        check_templates_in_provider.delay(provider.id)


@singleton_task(soft_time_limit=180)
def check_templates_in_provider(self, provider_id):
    self.logger.info("Initiated a periodic template check for {}".format(provider_id))
    provider = Provider.objects.get(id=provider_id)
    # Get templates and update metadata
    try:
        templates = map(str, provider.api.list_template())
    except:
        provider.working = False
        provider.save()
    else:
        provider.working = True
        provider.save()
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
            self.logger.info(
                "I will delete orphaned appliance {}/{}".format(appliance.id, appliance.name))
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
            self.logger.info("Killing broken appliance {}/{}".format(appliance.id, appliance.name))
            Appliance.kill(appliance)  # Use kill because the appliance may still exist
    # And now - if something happened during appliance deletion, call kill again
    for appliance in Appliance.objects.filter(
            marked_for_deletion=True, status_changed__lt=expiration_time).all():
        with transaction.atomic():
            appl = Appliance.objects.get(pk=appliance.pk)
            appl.marked_for_deletion = False
            appl.save()
        self.logger.info(
            "Trying to kill unkilled appliance {}/{}".format(appliance.id, appliance.name))
        Appliance.kill(appl)


def generic_shepherd(self, preconfigured):
    """This task takes care of having the required templates spinned into required number of
    appliances. For each template group, it keeps the last template's appliances spinned up in
    required quantity. If new template comes out of the door, it automatically kills the older
    running template's appliances and spins up new ones. Sorts the groups by the fulfillment."""
    for grp in sorted(
            Group.objects.all(), key=lambda g: g.get_fulfillment_percentage(preconfigured)):
        group_versions = Template.get_versions(
            template_group=grp, ready=True, usable=True, preconfigured=preconfigured)
        group_dates = Template.get_dates(
            template_group=grp, ready=True, usable=True, preconfigured=preconfigured)
        if group_versions:
            # Downstream - by version (downstream releases)
            version = group_versions[0]
            # Find the latest date (one version can have new build)
            dates = Template.get_dates(
                template_group=grp, ready=True, usable=True, version=group_versions[0],
                preconfigured=preconfigured)
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
                usable=True, ready=True, template_group=grp, preconfigured=preconfigured,
                **filter_keep).all())
        # If it can be deployed, it must exist
        possible_templates_for_provision = filter(lambda tpl: tpl.exists, possible_templates)
        appliances = []
        for template in possible_templates:
            appliances.extend(
                Appliance.objects.filter(
                    template=template, appliance_pool=None, marked_for_deletion=False))
        # If we then want to delete some templates, better kill the eldest. status_changed
        # says which one was provisioned when, because nothing else then touches that field.
        appliances.sort(key=lambda appliance: appliance.status_changed)
        pool_size = grp.template_pool_size if preconfigured else grp.unconfigured_template_pool_size
        if len(appliances) < pool_size and possible_templates_for_provision:
            # There must be some templates in order to run the provisioning
            # Provision ONE appliance at time for each group, that way it is possible to maintain
            # reasonable balancing
            new_appliance_name = settings.APPLIANCE_FORMAT.format(
                group=template.template_group.id,
                date=template.date.strftime("%y%m%d"),
                rnd=fauxfactory.gen_alphanumeric(8))
            with transaction.atomic():
                # Now look for templates that are on non-busy providers
                tpl_free = filter(
                    lambda t: t.provider.free,
                    possible_templates_for_provision)
                if tpl_free:
                    appliance = Appliance(
                        template=sorted(tpl_free, key=lambda t: t.provider.appliance_load)[0],
                        name=new_appliance_name)
                    appliance.save()
            if tpl_free:
                self.logger.info(
                    "Adding an appliance to shepherd: {}/{}".format(appliance.id, appliance.name))
                clone_template_to_appliance.delay(appliance.id, None)
        elif len(appliances) > pool_size:
            # Too many appliances, kill the surplus
            for appliance in appliances[:len(appliances) - pool_size]:
                self.logger.info("Killing an extra appliance {}/{} in shepherd".format(
                    appliance.id, appliance.name))
                Appliance.kill(appliance)

        # Killing old appliances
        for filter_kill in filters_kill:
            for template in Template.objects.filter(
                    ready=True, usable=True, template_group=grp, preconfigured=preconfigured,
                    **filter_kill):
                for a in Appliance.objects.filter(
                        template=template, appliance_pool=None, marked_for_deletion=False):
                    self.logger.info(
                        "Killing appliance {}/{} in shepherd because it is obsolete now".format(
                            a.id, a.name))
                    Appliance.kill(a)


@singleton_task()
def free_appliance_shepherd(self):
    generic_shepherd(self, True)
    generic_shepherd(self, False)


@singleton_task()
def wait_appliance_ready(self, appliance_id):
    """This task checks for appliance's readiness for use. The checking loop is designed as retrying
    the task to free up the queue."""
    try:
        appliance = Appliance.objects.get(id=appliance_id)
        if appliance.appliance_pool is not None:
            if appliance.appliance_pool.not_needed_anymore:
                # Terminate task chain
                self.request.callbacks[:] = []
                kill_appliance.delay(appliance_id)
                return
        if appliance.power_state == Appliance.Power.UNKNOWN or appliance.ip_address is None:
            self.retry(args=(appliance_id,), countdown=30, max_retries=45)
        if Appliance.objects.get(id=appliance_id).cfme.ipapp.is_web_ui_running():
            with transaction.atomic():
                appliance = Appliance.objects.get(id=appliance_id)
                appliance.ready = True
                appliance.save()
            appliance.set_status("The appliance is ready.")
            with diaper:
                appliance.synchronize_metadata()
        else:
            with transaction.atomic():
                appliance = Appliance.objects.get(id=appliance_id)
                appliance.ready = False
                appliance.save()
            appliance.set_status("Waiting for UI to appear.")
            self.retry(args=(appliance_id,), countdown=30, max_retries=45)
    except ObjectDoesNotExist:
        # source object is not present, terminating
        return


@singleton_task()
def anyvm_power_on(self, provider, vm):
    provider = get_mgmt(provider)
    provider.start_vm(vm)


@singleton_task()
def anyvm_power_off(self, provider, vm):
    provider = get_mgmt(provider)
    provider.stop_vm(vm)


@singleton_task()
def anyvm_suspend(self, provider, vm):
    provider = get_mgmt(provider)
    provider.suspend_vm(vm)


@singleton_task()
def anyvm_delete(self, provider, vm):
    provider = get_mgmt(provider)
    provider.delete_vm(vm)


@singleton_task()
def delete_template_from_provider(self, template_id):
    template = Template.objects.get(id=template_id)
    try:
        template.provider_api.delete_template(template.name)
    except Exception as e:
        self.logger.exception(e)
        return False
    with transaction.atomic():
        template = Template.objects.get(pk=template.pk)
        template.exists = False
        template.save()
    return True


@singleton_task()
def appliance_rename(self, appliance_id, new_name):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        return None
    if appliance.name == new_name:
        return None
    with redis.appliances_ignored_when_renaming(appliance.name, new_name):
        self.logger.info("Renaming {}/{} to {}".format(appliance_id, appliance.name, new_name))
        appliance.name = appliance.provider_api.rename_vm(appliance.name, new_name)
        appliance.save()
    return appliance.name


@singleton_task()
def rename_appliances_for_pool(self, pool_id):
    with transaction.atomic():
        try:
            appliance_pool = AppliancePool.objects.get(id=pool_id)
        except ObjectDoesNotExist:
            return
        appliances = [
            appliance
            for appliance
            in appliance_pool.appliances
            if appliance.provider_api.can_rename
        ]
        for appliance in appliances:
            new_name = "{}-{}-{}".format(
                appliance_pool.owner.username,
                appliance_pool.group.id,
                appliance.template.date.strftime("%y%m%d")
            )
            if appliance.template.version:
                new_name += "-{}".format(appliance.template.version)
            new_name += "-{}".format(fauxfactory.gen_alphanumeric(length=4))
            appliance_rename.apply_async(
                countdown=10,  # To prevent clogging with the transaction.atomic
                args=(appliance.id, new_name))


@singleton_task(soft_time_limit=60)
def check_update(self):
    sprout_sh = project_path.join("sprout").join("sprout.sh")
    try:
        result = command.run([sprout_sh.strpath, "check-update"])
    except command.CommandException as e:
        result = e
    needs_update = result.output.strip().lower() != "up-to-date"
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


@singleton_task()
def mailer_version_mismatch(self):
    """This is usually called per-mismatch, but as the mismatches are stored in database and the
    mail can fail sending, so this can send the mismatches in a batch in this case."""
    with transaction.atomic():
        mismatches = MismatchVersionMailer.objects.filter(sent=False)
        if not mismatches:
            return
        email_body = """\
Hello,

I am Sprout template version mismatch spammer. I think there are some version mismatches.

Here is the list:

{}

Sincerely,
Sprout template version mismatch spammer™
        """.format(
            "\n".join(
                "* {} @ {} : supposed {} , true {}".format(
                    mismatch.template_name, mismatch.provider.id, mismatch.supposed_version,
                    mismatch.actual_version)
                for mismatch in mismatches
            )
        )
        user_mails = []
        for user in User.objects.filter(is_superuser=True):
            if user.email:
                user_mails.append(user.email)
        result = send_mail(
            "Template version mismatches detected",
            email_body,
            "sprout-template-version-mismatch@example.com",
            user_mails,
        )
        if result > 0:
            for mismatch in mismatches:
                mismatch.sent = True
                mismatch.save()


@singleton_task()
def obsolete_template_deleter(self):
    for group in Group.objects.all():
        if group.template_obsolete_days_delete:
            # We can delete based on the template age
            obsolete_templates = group.obsolete_templates
            if obsolete_templates is not None:
                for template in obsolete_templates:
                    if template.can_be_deleted:
                        delete_template_from_provider.delay(template.id)


@singleton_task()
def connect_direct_lun(self, appliance_id):
    appliance = Appliance.objects.get(id=appliance_id)
    if not hasattr(appliance.provider_api, "connect_direct_lun_to_appliance"):
        return False
    try:
        appliance.provider_api.connect_direct_lun_to_appliance(appliance.name, False)
    except Exception as e:
        appliance.set_status("LUN: {}: {}".format(type(e).__name__, str(e)))
        return False
    else:
        appliance.reload()
        with transaction.atomic():
            appliance.lun_disk_connected = True
            appliance.save()
        return True


@singleton_task()
def disconnect_direct_lun(self, appliance_id):
    appliance = Appliance.objects.get(id=appliance_id)
    if not appliance.lun_disk_connected:
        return False
    if not hasattr(appliance.provider_api, "connect_direct_lun_to_appliance"):
        return False
    try:
        appliance.provider_api.connect_direct_lun_to_appliance(appliance.name, True)
    except Exception as e:
        appliance.set_status("LUN: {}: {}".format(type(e).__name__, str(e)))
        return False
    else:
        appliance.reload()
        with transaction.atomic():
            appliance.lun_disk_connected = False
            appliance.save()
        return True


@singleton_task()
def appliance_yum_update(self, appliance_id):
    appliance = Appliance.objects.get(id=appliance_id)
    appliance.ipapp.update_rhel(reboot=False)


@singleton_task()
def pick_templates_for_deletion(self):
    """Applies some heuristics to guess templates that might be candidates to deletion."""
    to_mail = {}
    for group in Group.objects.all():
        for zstream, versions in group.pick_versions_to_delete().iteritems():
            for version in versions:
                for template in Template.objects.filter(
                        template_group=group, version=version, exists=True, suggested_delete=False):
                    template.suggested_delete = True
                    template.save()
                    if group.id not in to_mail:
                        to_mail[group.id] = {}
                    if zstream not in to_mail[group.id]:
                        to_mail[group.id][zstream] = {}
                    if version not in to_mail[group.id][zstream]:
                        to_mail[group.id][zstream][version] = []
                    to_mail[group.id][zstream][version].append(
                        "{} @ {}".format(template.name, template.provider.id))
    # TODO: Figure out why it was spamming
    if to_mail and False:
        data = yaml.safe_dump(to_mail, default_flow_style=False)
        email_body = """\
Hello,

just letting you know that there are some templates that you might like to delete:

{}

Visit Sprout's Templates page for more informations.

Sincerely,
Sprout.
        """.format(data)
        user_mails = []
        for user in User.objects.filter(is_superuser=True):
            if user.email:
                user_mails.append(user.email)
        send_mail(
            "Possible candidates for template deletion",
            email_body,
            "sprout-template-deletion-suggest@example.com",
            user_mails,
        )


@singleton_task()
def check_swap_in_appliances(self):
    chord_tasks = []
    for appliance in Appliance.objects.filter(
            ready=True, power_state=Appliance.Power.ON, marked_for_deletion=False).exclude(
            power_state=Appliance.Power.ORPHANED):
        chord_tasks.append(check_swap_in_appliance.si(appliance.id))
    chord(chord_tasks)(notify_owners.s())


@singleton_task()
def check_swap_in_appliance(self, appliance_id):
    appliance = Appliance.objects.get(id=appliance_id)

    try:
        swap_amount = appliance.ipapp.swap
    except (SSHException, socket.error, Exception) as e:
        if type(e) is Exception and 'SSH is unavailable' not in str(e):
            # Because otherwise it might not be an SSH error
            raise
        ssh_failed = True
        swap_amount = None
    else:
        ssh_failed = False

    went_up = (
        (appliance.swap is not None and swap_amount > appliance.swap) or
        (appliance.swap is None and swap_amount is not None and swap_amount > 0))

    ssh_failed_changed = ssh_failed and not appliance.ssh_failed

    appliance.swap = swap_amount
    appliance.ssh_failed = ssh_failed
    appliance.save()

    # Returns a tuple - (appliance_id, went_up?, current_amount, ssh_failed?)
    return appliance.id, went_up, swap_amount, ssh_failed_changed


@singleton_task()
def notify_owners(self, results):
    # Filter out any errors
    results = [x for x in results if isinstance(x, (list, tuple)) and len(x) == 4]
    per_user = {}
    for appliance_id, went_up, current_swap, ssh_failed_changed in results:
        if not went_up and not ssh_failed_changed:
            # Not interested
            continue
        appliance = Appliance.objects.get(id=appliance_id)
        if appliance.appliance_pool is not None:
            username = appliance.appliance_pool.owner.username
            user = appliance.appliance_pool.owner
        else:
            username = 'SHEPHERD'
            user = None
        issues = []
        if went_up:
            issues.append('swap++ {}M'.format(current_swap))
        if ssh_failed_changed:
            issues.append('ssh unreachable')

        message = '{}/{} {}'.format(
            appliance.name, appliance.ip_address, ', '.join(issues))

        if user is None:
            # No email
            continue

        if not user.email:
            # Same here
            continue

        # We assume that "living" users have an e-mail set therefore we will not nag about bots'
        # appliances.
        send_message('{}: {}'.format(username, message))

        # Add the message to be sent
        if user not in per_user:
            per_user[user] = []
        per_user[user].append(message)

    # Send out the e-mails
    for user, messages in per_user.iteritems():
        appliance_list = '\n'.join('* {}'.format(message) for message in messages)
        email_body = """\
Hello,

I discovered that some of your appliances are behaving badly. Please check them out:
{}

Best regards,
The Sprout™
""".format(appliance_list)
        send_mail(
            "[Sprout] Appliance swap report",
            email_body,
            "sprout-appliance-swap@example.com",
            [user.email],
        )


@singleton_task()
def appliances_synchronize_metadata(self):
    for appliance in Appliance.objects.all():
        appliance_synchronize_metadata.delay(appliance.id)


@singleton_task()
def appliance_synchronize_metadata(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        return
    appliance.synchronize_metadata()


@singleton_task()
def synchronize_untracked_vms(self):
    for provider in Provider.objects.filter(working=True, disabled=False):
        synchronize_untracked_vms_in_provider.delay(provider.id)


def parsedate(d):
    if d is None:
        return d
    else:
        return iso8601.parse_date(d)


@singleton_task()
def synchronize_untracked_vms_in_provider(self, provider_id):
    """'re'-synchronizes any vms that might be lost during outages."""
    provider = Provider.objects.get(id=provider_id)
    provider_api = provider.api
    for vm_name in sorted(map(str, provider_api.list_vm())):
        if Appliance.objects.filter(name=vm_name, template__provider=provider).count() != 0:
            continue
        # We have an untracked VM. Let's investigate
        try:
            appliance_id = provider_api.get_meta_value(vm_name, 'sprout_id')
        except KeyError:
            continue
        except NotImplementedError:
            # Do not bother if not implemented in the API
            return

        # just check it again ...
        if Appliance.objects.filter(id=appliance_id).count() == 1:
            # For some reason it is already in
            continue

        # Now it appears that this is a VM that was in Sprout
        construct = {'id': appliance_id}
        # Retrieve appliance data
        try:
            self.logger.info('Trying to reconstruct appliance %d/%s', appliance_id, vm_name)
            construct['name'] = vm_name
            template_id = provider_api.get_meta_value(vm_name, 'sprout_source_template_id')
            # Templates are not deleted from the DB so this should be OK.
            construct['template'] = Template.objects.get(id=template_id)
            construct['name'] = vm_name
            construct['ready'] = provider_api.get_meta_value(vm_name, 'sprout_ready')
            construct['description'] = provider_api.get_meta_value(vm_name, 'sprout_description')
            construct['lun_disk_connected'] = provider_api.get_meta_value(
                vm_name, 'sprout_lun_disk_connected')
            construct['swap'] = provider_api.get_meta_value(vm_name, 'sprout_swap')
            construct['ssh_failed'] = provider_api.get_meta_value(vm_name, 'sprout_ssh_failed')
            # Time fields
            construct['datetime_leased'] = parsedate(
                provider_api.get_meta_value(vm_name, 'sprout_datetime_leased'))
            construct['leased_until'] = parsedate(
                provider_api.get_meta_value(vm_name, 'sprout_leased_until'))
            construct['status_changed'] = parsedate(
                provider_api.get_meta_value(vm_name, 'sprout_status_changed'))
        except KeyError as e:
            self.logger.error('Failed to reconstruct %d/%s', appliance_id, vm_name)
            self.logger.exception(e)
            continue
        # Retrieve pool data if applicable
        try:
            pool_id = provider_api.get_meta_value(vm_name, 'sprout_pool_id')
            pool_construct = {'id': pool_id}
            pool_construct['total_count'] = provider_api.get_meta_value(
                vm_name, 'sprout_pool_total_count')
            group_id = provider_api.get_meta_value(
                vm_name, 'sprout_pool_group')
            pool_construct['group'] = Group.objects.get(id=group_id)
            try:
                pool_construct['provider'] = provider_api.get_meta_value(
                    vm_name, 'sprout_pool_provider')
            except KeyError:
                # optional
                pool_construct['provider'] = None
            pool_construct['version'] = provider_api.get_meta_value(
                vm_name, 'sprout_pool_version')
            pool_construct['date'] = parsedate(provider_api.get_meta_value(
                vm_name, 'sprout_pool_appliance_date'))
            owner_id = provider_api.get_meta_value(
                vm_name, 'sprout_pool_owner_id')
            try:
                owner = User.objects.get(id=owner_id)
            except ObjectDoesNotExist:
                owner_username = provider_api.get_meta_value(
                    vm_name, 'sprout_pool_owner_username')
                owner = User(id=owner_id, username=owner_username)
                owner.save()
            pool_construct['owner'] = owner
            pool_construct['preconfigured'] = provider_api.get_meta_value(
                vm_name, 'sprout_pool_preconfigured')
            pool_construct['description'] = provider_api.get_meta_value(
                vm_name, 'sprout_pool_description')
            pool_construct['not_needed_anymore'] = provider_api.get_meta_value(
                vm_name, 'sprout_pool_not_needed_anymore')
            pool_construct['finished'] = provider_api.get_meta_value(
                vm_name, 'sprout_pool_finished')
            pool_construct['yum_update'] = provider_api.get_meta_value(
                vm_name, 'sprout_pool_yum_update')
            try:
                construct['appliance_pool'] = AppliancePool.objects.get(id=pool_id)
            except ObjectDoesNotExist:
                pool = AppliancePool(**pool_construct)
                pool.save()
                construct['appliance_pool'] = pool
        except KeyError as e:
            pass

        appliance = Appliance(**construct)
        appliance.save()

        # And now, refresh!
        refresh_appliances_provider.delay(provider.id)
