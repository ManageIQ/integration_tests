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
from contextlib import closing
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from celery import chain, chord, shared_task
from celery.exceptions import MaxRetriesExceededError
from datetime import datetime, timedelta
from functools import wraps
from lxml import etree
from miq_version import Version, TemplateName
from novaclient.exceptions import OverLimit as OSOverLimit
from paramiko import SSHException
from urllib2 import urlopen, HTTPError
import socket

from appliances.models import (
    Provider, Group, Template, Appliance, AppliancePool, DelayedProvisionTask,
    MismatchVersionMailer, User, GroupShepherd)
from sprout import settings, redis
from sprout.irc_bot import send_message
from sprout.log import create_logger

from cfme.utils import conf
from cfme.utils.appliance import Appliance as CFMEAppliance
from cfme.utils.path import project_path
from cfme.utils.timeutil import parsetime
from cfme.utils.trackerbot import api, depaginate
from cfme.utils.wait import wait_for

from wrapanapi import VmState, Openshift

LOCK_EXPIRE = 60 * 15  # 15 minutes
TRACKERBOT_PAGINATE = 100


def gen_appliance_name(template_id, username=None):
    template = Template.objects.get(id=template_id)
    if template.template_type != Template.OPENSHIFT_POD:
        appliance_format = settings.APPLIANCE_FORMAT
    else:
        appliance_format = settings.OPENSHIFT_APPLIANCE_FORMAT

    new_appliance_name = appliance_format.format(
        group=template.template_group.id,
        date=template.date.strftime("%y%m%d"),
        rnd=fauxfactory.gen_alphanumeric(8).lower())

    # Apply also username
    if username:
        new_appliance_name = "{}_{}".format(username, new_appliance_name)
        if template.template_type == Template.OPENSHIFT_POD:
            # openshift doesn't allow underscores to be used in project names
            new_appliance_name = new_appliance_name.replace('_', '-')
    return new_appliance_name


def trackerbot():
    return api(trackerbot_url=settings.HUBBER_URL.rstrip('/') + '/api/')


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
            try:
                return task(self, *args, **kwargs)
            except Exception as e:
                self.logger.error(
                    "An exception occured when executing with args: %r kwargs: %r",
                    args, kwargs)
                self.logger.exception(e)
                raise
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
                try:
                    return task(self, *args, **kwargs)
                except Exception as e:
                    self.logger.error(
                        "An exception occured when executing with args: %r kwargs: %r",
                        args, kwargs)
                    self.logger.exception(e)
                    raise
                finally:
                    cache.delete(lock_id)
            elif wait:
                self.logger.info("Waiting for another instance of the task to end.")
                self.retry(args=args, countdown=wait_countdown, max_retries=wait_retries)

        return shared_task(*args, **kwargs)(wrapped_task)
    return f


@singleton_task()
def kill_unused_appliances(self):
    """This is the watchdog, that guards the appliances that were given to users. If you forget
    to prolong the lease time, this is the thing that will take the appliance off your hands
    and kill it."""
    with transaction.atomic():
        for appliance in Appliance.objects.filter(marked_for_deletion=False):
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
    appliance = Appliance.objects.get(id=appliance_id)
    workflow = [
        disconnect_direct_lun.si(appliance_id),
        appliance_power_off.si(appliance_id),
        kill_appliance_delete.si(appliance_id),
    ]
    if replace_in_pool:
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
def poke_trackerbot(self):
    """This beat-scheduled task periodically polls the trackerbot if there are any new templates.
    """
    template_usability = []
    # Extract data from trackerbot
    tbapi = trackerbot()
    objects = depaginate(tbapi, tbapi.providertemplate().get(limit=TRACKERBOT_PAGINATE))["objects"]
    per_group = {}
    for obj in objects:
        if obj["template"]["group"]["name"] == 'unknown':
            continue
        if obj["template"]["group"]["name"] not in per_group:
            per_group[obj["template"]["group"]["name"]] = []

        per_group[obj["template"]["group"]["name"]].append(obj)
    # Sort them using the build date
    for group in per_group.keys():
        per_group[group] = sorted(
            per_group[group],
            reverse=True, key=lambda o: o["template"]["datestamp"])
    objects = []
    # And interleave the the groups
    while any(per_group.values()):
        for key in per_group.keys():
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
        if not provider.provider_type:
            provider.provider_type = provider.provider_data.get('type')
            provider.save(update_fields=['provider_type'])
        template_name = template["template"]["name"]
        ga_released = template['template']['ga_released']

        custom_data = template['template'].get('custom_data', "{}")
        processed_custom_data = yaml.safe_load(custom_data)

        template_info = TemplateName.parse_template(template_name)
        if not template_info.datestamp:
            # Not a CFME/MIQ template, ignore it.
            continue
        # Original one
        original_template = None
        try:
            original_template = Template.objects.get(
                provider=provider, template_group=group, original_name=template_name,
                name=template_name, preconfigured=False)
            if original_template.ga_released != ga_released:
                original_template.ga_released = ga_released
                original_template.save(update_fields=['ga_released'])
            if provider.provider_type == 'openshift':
                if original_template.custom_data != custom_data:
                    original_template.custom_data = processed_custom_data
                original_template.template_type = Template.OPENSHIFT_POD
                original_template.container = 'cloudforms-0'
                original_template.save(update_fields=['custom_data',
                                                      'container',
                                                      'template_type'])
        except ObjectDoesNotExist:
            if template_name in provider.templates:
                if template_info.datestamp is None:
                    self.logger.warning("Ignoring template {} because it does not have a date!"
                                        .format(template_name))
                    continue
                template_version = template_info.version
                if template_version is None:
                    # Make up a faux version
                    # First 3 fields of version get parsed as a zstream
                    # therefore ... makes it a "nil" stream
                    template_version = "...{}".format(template_info.datestamp.strftime("%Y%m%d"))
                with transaction.atomic():
                    tpl = Template(
                        provider=provider, template_group=group, original_name=template_name,
                        name=template_name, preconfigured=False, date=template_info.datestamp,
                        ready=True, exists=True, usable=True, version=template_version)
                    tpl.save()
                    if provider.provider_type == 'openshift':
                        tpl.custom_data = processed_custom_data
                        tpl.container = 'cloudforms-0'
                        tpl.template_type = Template.OPENSHIFT_POD
                        tpl.save(update_fields=['container', 'template_type', 'custom_data'])
                    original_template = tpl
                    self.logger.info("Created a new template #{}".format(tpl.id))
        # If the provider is set to not preconfigure templates, do not bother even doing it.
        if provider.num_simultaneous_configuring > 0:
            # Preconfigured one
            try:
                # openshift providers don't have preconfigured templates.
                # so regular template should be used
                if provider.provider_type != 'openshift':
                    preconfigured_template = Template.objects.get(
                        provider=provider, template_group=group, original_name=template_name,
                        preconfigured=True)
                else:
                    preconfigured_template = Template.objects.get(
                        provider=provider, template_group=group, name=template_name,
                        preconfigured=True)
                    preconfigured_template.custom_data = processed_custom_data
                    preconfigured_template.container = 'cloudforms-0'
                    preconfigured_template.template_type = Template.OPENSHIFT_POD
                    preconfigured_template.save(update_fields=['container',
                                                               'template_type',
                                                               'custom_data'])
                if preconfigured_template.ga_released != ga_released:
                    preconfigured_template.ga_released = ga_released
                    preconfigured_template.save(update_fields=['ga_released'])

            except ObjectDoesNotExist:
                if template_name in provider.templates and provider.provider_type != 'openshift':
                    original_id = original_template.id if original_template is not None else None
                    create_appliance_template.delay(
                        provider.id, group.id, template_name, source_template_id=original_id)
    # If any of the templates becomes unusable, let sprout know about it
    # Similarly if some of them becomes usable ...
    for provider_id, template_name, usability in template_usability:
        provider, create = Provider.objects.get_or_create(id=provider_id)
        if not provider.working or provider.disabled:
            continue
        with transaction.atomic():
            for template in Template.objects.filter(provider=provider, original_name=template_name):
                template.usable = usability
                template.save(update_fields=['usable'])
                # Kill all shepherd appliances if they were accidentally spun up
                if not usability:
                    for appliance in Appliance.objects.filter(
                            template=template, marked_for_deletion=False,
                            appliance_pool=None):
                        self.logger.info(
                            'Killing an appliance {}/{} because its template was marked as unusable'
                            .format(appliance.id, appliance.name))
                        Appliance.kill(appliance)


@logged_task()
def create_appliance_template(self, provider_id, group_id, template_name, source_template_id=None):
    """This task creates a template from a fresh CFME template. In case of fatal error during the
    operation, the template object is deleted to make sure the operation will be retried next time
    when poke_trackerbot runs."""
    provider = Provider.objects.get(id=provider_id, working=True, disabled=False)
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
        template_info = TemplateName.parse_template(template_name)
        template_date_fmt = template_info.datestamp.strftime("%Y%m%d")
        if not template_info.datestamp:
            return
        # Make up a faux version
        # First 3 fields of version get parsed as a zstream
        # therefore ... makes it a "nil" stream
        template_version = template_info.version or "...{}".format(template_date_fmt)

        new_template_name = settings.TEMPLATE_FORMAT.format(group=group.id,
                                                            date=template_date_fmt,
                                                            rnd=fauxfactory.gen_alphanumeric(8))
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
                        group=group.id[:2], date=template_date_fmt,  # Use only first 2 of grp
                        rnd=fauxfactory.gen_alphanumeric(2))  # And just 2 chars random
                    # TODO: If anything larger comes, do fix that!
        if source_template_id is not None:
            try:
                source_template = Template.objects.get(id=source_template_id)
            except ObjectDoesNotExist:
                source_template = None
        else:
            source_template = None
        template = Template(provider=provider,
                            template_group=group,
                            name=new_template_name,
                            date=template_info.datestamp,
                            version=template_version,
                            original_name=template_name, parent_template=source_template,
                            exists=False)
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
        if not template.provider.is_working:
            raise RuntimeError('Provider {} is not working.'.format(template.provider))
        if template.vm_mgmt is None or not template.vm_mgmt.exists:
            template.set_status("Deploying the template.")
            provider_data = template.provider.provider_data
            kwargs = provider_data["sprout"]
            kwargs["power_on"] = True
            if "datastore" not in kwargs and "allowed_datastore" in provider_data:
                kwargs["datastore"] = provider_data["allowed_datastore"]
            self.logger.info("Deployment kwargs: {}".format(repr(kwargs)))

            # TODO: change after openshift wrapanapi refactor
            vm = None
            if isinstance(template.provider_api, Openshift):
                template.provider_api.deploy_template(
                    template.original_name, vm_name=template.name, **kwargs)
            else:
                vm = template.source_template_mgmt.deploy(vm_name=template.name, **kwargs)
                vm.ensure_state(VmState.RUNNING)
        else:
            template.set_status("Waiting for deployment to be finished.")
            # TODO: change after openshift wrapanapi refactor
            if isinstance(template.provider_api, Openshift):
                template.provider_api.wait_vm_running(template.name)

    except Exception as e:
        template.set_status(
            "Could not properly deploy the template. Retrying. {}: {}".format(
                type(e).__name__, str(e)))
        self.logger.exception(e)
        self.retry(args=(template_id,), exc=e, countdown=10, max_retries=5)
    else:
        template.set_status("Template deployed.")


@singleton_task()
def prepare_template_verify_version(self, template_id):
    template = Template.objects.get(id=template_id)
    template.set_status("Verifying version.")
    appliance = CFMEAppliance.from_provider(
        template.provider_name, template.name, container=template.container)
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
        t = str(true_version)
        s = str(supposed_version)
        if supposed_version.version == true_version.version or t.startswith(s):
            # The two have same version but different suffixes, apply the suffix to the template obj
            # OR also a case - when the supposed version is incomplete so we will use the detected
            # version.
            with transaction.atomic():
                template.version = t
                template.save(update_fields=['version'])
                if template.parent_template is not None:
                    # In case we have a parent template, update the version there too.
                    if template.version != template.parent_template.version:
                        pt = template.parent_template
                        pt.version = template.version
                        pt.save(update_fields=['version'])
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
    appliance = CFMEAppliance.from_provider(
        template.provider_name, template.name, container=template.container)
    try:
        appliance.configure(
            setup_fleece=False,
            log_callback=lambda s: template.set_status("Customization progress: {}".format(s)),
            on_openstack=template.provider.provider_data.get('type', None) == 'openstack')
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
    try:
        if not template.provider.is_working:
            raise RuntimeError('Provider {} is not working.'.format(template.provider))
        template.set_status("Powering off")
        # TODO: change after openshift wrapanapi refactor
        if isinstance(template.provider_api, Openshift):
            template.provider_api.stop_vm(template.name)
            template.provider_api.wait_vm_stopped(template.name)
        else:
            template.vm_mgmt.ensure_state(VmState.STOPPED)
    except Exception as e:
        template.set_status("Could not power off the appliance. Retrying.")
        self.retry(args=(template_id,), exc=e, countdown=10, max_retries=5)
    else:
        template.set_status("Powered off.")


@singleton_task()
def prepare_template_finish(self, template_id):
    template = Template.objects.get(id=template_id)
    try:
        if not template.provider.is_working:
            raise RuntimeError('Provider {} is not working.'.format(template.provider))
        template.set_status("Finishing template creation with an api mark_as_template call")
        # TODO: change after openshift wrapanapi refactor
        if isinstance(template.provider_api, Openshift):
            template.provider_api.mark_as_template(template.name, delete_on_error=True)
        else:
            # virtualcenter may want to store templates on different datastore
            # migrate if necessary
            if template.provider.provider_type == 'virtualcenter':
                host = (template.provider.provider_data.get('template_upload', {}).get('host') or
                        template.provider_api.list_host().pop())
                datastore = template.provider.provider_data.get('template_upload',
                                                                {}).get('template_datastore')
                if host is not None and datastore is not None:
                    template.set_status("Migrating VM before mark_as_template for vmware")
                    template.vm_mgmt.clone(vm_name=template.name,
                                       datastore=datastore,
                                       host=host,
                                       relocate=True)
                # we now have a cloned VM with temporary name to mark as the template
                template.vm_mgmt.mark_as_template(template.name, delete_on_error=True)
            else:
                template.vm_mgmt.mark_as_template(template.name, delete_on_error=True)
        with transaction.atomic():
            template = Template.objects.get(id=template_id)
            template.ready = True
            template.exists = True
            template.save(update_fields=['ready', 'exists'])
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
    try:
        if not template.provider.is_working:
            raise RuntimeError('Provider is not working.')
        template.set_status("Template creation failed. Deleting it.")
        if template.provider_api.does_vm_exist(template.name):
            # TODO: change after openshift wrapanapi refactor
            if isinstance(template.provider_api, Openshift):
                template.provider_api.delete_vm(template.name)
            else:
                template.vm_mgmt.cleanup()
            wait_for(template.provider_api.does_vm_exist, [template.name], timeout='5m', delay=10)
        if template.provider_api.does_template_exist(template.name):
            # TODO: change after openshift wrapanapi refactor
            if isinstance(template.provider_api, Openshift):
                template.provider_api.delete_template(template.name)
            else:
                template.provider_api.get_template(template.name).cleanup()
            wait_for(
                template.provider_api.does_template_exist, [template.name], timeout='5m', delay=10)
        if (template.temporary_name is not None and
                template.provider_api.does_template_exist(template.temporary_name)):
            # TODO: change after openshift wrapanapi refactor
            if isinstance(template.provider_api, Openshift):
                template.provider_api.delete_template(template.temporary_name)
            else:
                template.provider_api.get_template(template.temporary_name).cleanup()
            wait_for(
                template.provider_api.does_template_exist,
                [template.temporary_name], timeout='5m', delay=10)
        template.delete()
    except Exception as e:
        self.retry(args=(template_id,), exc=e, countdown=60, max_retries=5)


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
        pool.logger.info("Applying lease time and renaming appliances")
        for appliance in pool.appliances:
            apply_lease_times.delay(appliance.id, time_minutes)
        with transaction.atomic():
            pool.finished = True
            pool.save(update_fields=['finished'])
            pool.logger.info("Pool {} setup is finished".format(appliance_pool_id))
    else:
        # Look whether we can swap any provisioning appliance with some in shepherd
        pool.logger.info("Pool isn't fulfilled yet")
        unfinished = list(
            Appliance.objects.filter(
                appliance_pool=pool, ready=False, marked_for_deletion=False).all())
        random.shuffle(unfinished)
        if len(unfinished) > 0:
            pool.logger.info('There are %s unfinished appliances', len(unfinished))
            n = Appliance.give_to_pool(pool, len(unfinished))
            with transaction.atomic():
                for _ in range(n):
                    appl = unfinished.pop()
                    appl.appliance_pool = None
                    appl.save(update_fields=['appliance_pool'])
        try:
            pool.logger.info("Retrying to apply lease again")
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
                        appl = random.choice(appliances)
                        self.logger.info(
                            'Freeing some space in provider by killing appliance {}/{}'
                            .format(appl.id, appl.name))
                        Appliance.kill(appl)
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
    templates = appliance_pool.possible_templates
    templates_excluded = filter(lambda tpl: tpl != exclude_template, templates)
    if templates_excluded:
        template = random.choice(templates_excluded)
    else:
        template = exclude_template  # :( no other template to use
    clone_template_to_pool(template.id, appliance_pool_id, time_minutes)


def clone_template_to_pool(template_id, appliance_pool_id, time_minutes):
    template = Template.objects.get(id=template_id)
    with transaction.atomic():
        pool = AppliancePool.objects.get(id=appliance_pool_id)
        if pool.not_needed_anymore:
            return

        new_appliance_name = gen_appliance_name(template_id, username=pool.owner.username)
        appliance = Appliance(template=template, name=new_appliance_name, appliance_pool=pool)
        appliance.save()
        # Set pool to these params to keep the appliances with same versions/dates
        pool.version = template.version
        pool.date = template.date
        pool.save(update_fields=['version', 'date'])
    clone_template_to_appliance.delay(appliance.id, time_minutes, pool.yum_update)


@logged_task()
def apply_lease_times(self, appliance_id, time_minutes):
    self.logger.info(
        "Applying lease time {} minutes on appliance {}".format(time_minutes, appliance_id))
    with transaction.atomic():
        appliance = Appliance.objects.get(id=appliance_id)
        appliance.datetime_leased = timezone.now()
        appliance.leased_until = appliance.datetime_leased + timedelta(minutes=int(time_minutes))
        appliance.save(update_fields=['datetime_leased', 'leased_until'])
        self.logger.info(
            "Lease time has been applied successfully "
            "on appliance {}, pool {}, provider {}".format(appliance_id,
                                                           appliance.appliance_pool.id,
                                                           appliance.provider_name))


@logged_task()
def clone_template(self, template_id):
    self.logger.info("Cloning template {}".format(template_id))
    template = Template.objects.get(id=template_id)
    new_appliance_name = gen_appliance_name(template_id)
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
        appliance_rename.si(appliance_id),
        appliance_set_ansible_url.si(appliance_id)
    ]
    if yum_update:
        tasks.append(appliance_yum_update.si(appliance_id))
        tasks.append(appliance_reboot.si(appliance_id, if_needs_restarting=True))
    if appliance.preconfigured:
        tasks.append(wait_appliance_ready.si(appliance_id))
        tasks.append(appliance_set_hostname.si(appliance_id))
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
    if not appliance.provider.is_working:
        raise RuntimeError('Provider {} is not working for appliance {}'
                           .format(appliance.provider, appliance.name))
    try:
        appliance.provider.cleanup()
        if not appliance.provider_api.does_vm_exist(appliance.name):
            appliance.set_status("Beginning template clone.")
            provider_data = appliance.template.provider.provider_data
            kwargs = dict(provider_data["sprout"])
            kwargs["power_on"] = False
            if "datastore" not in kwargs and 'allowed_datastore' in kwargs:
                kwargs["datastore"] = kwargs.pop("allowed_datastore")
            if appliance.appliance_pool is not None:
                if appliance.appliance_pool.override_memory is not None:
                    kwargs['ram'] = appliance.appliance_pool.override_memory
                if appliance.appliance_pool.override_cpu is not None:
                    kwargs['cpu'] = appliance.appliance_pool.override_cpu
            if appliance.is_openshift and appliance.template.custom_data:
                kwargs['tags'] = appliance.template.custom_data.get('TAGS')

            # TODO: change after openshift wrapanapi refactor
            if appliance.is_openshift:
                vm_data = appliance.provider_api.deploy_template(
                    appliance.template.name,
                    vm_name=appliance.name,
                    progress_callback=lambda progress: appliance.set_status(
                        "Deploy progress: {}".format(progress)),
                    **kwargs
                )
                with transaction.atomic():
                    appliance.openshift_ext_ip = vm_data['external_ip']
                    appliance.openshift_project = vm_data['project']
                    appliance.ip_address = vm_data['url']
                    appliance.save(update_fields=['openshift_ext_ip',
                                                  'openshift_project',
                                                  'ip_address'])
            else:
                appliance.template_mgmt.deploy(
                    vm_name=appliance.name,
                    progress_callback=lambda progress: appliance.set_status(
                        "Deploy progress: {}".format(progress)),
                    **kwargs
                )
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

        # Ignore that and provision it somewhere else
        if appliance.appliance_pool:
            # We can put it aside for a while to wait for
            self.request.callbacks[:] = []  # Quit this chain
            pool = appliance.appliance_pool
            try:
                if appliance.provider_api.does_vm_exist(appliance.name):
                    appliance.set_status("Clonning finished with errors. So, removing vm")
                    # Better to check it, you never know when does that fail
                    # TODO: change after openshift wrapanapi refactor
                    if appliance.is_openshift:
                        appliance.provider_api.delete_vm(appliance.name)
                    else:
                        appliance.vm_mgmt.cleanup()

                    wait_for(
                        appliance.provider_api.does_vm_exist,
                        [appliance.name], timeout='5m', delay=10)
            except Exception:
                pass  # Diaper here

            self.logger.warning('Appliance %s was not deployed correctly. '
                                'It has to be redeployed', appliance_id)
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
    if not appliance.provider.is_working:
        raise RuntimeError('Provider {} is not working for appliance {}'
                           .format(appliance.provider, appliance.name))
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
        appliance.save(update_fields=['ready'])
    Appliance.objects.get(id=appliance_id).set_status("Appliance was marked as ready")


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
            # TODO: change after openshift wrapanapi refactor
            if appliance.is_openshift:
                try:
                    current_ip = appliance.provider_api.current_ip_address(appliance.name)
                except Exception:
                    current_ip = None
            else:
                current_ip = appliance.vm_mgmt.ip
            if current_ip is not None:
                # IP present
                Appliance.objects.get(id=appliance_id).set_status("Appliance was powered on.")
                with transaction.atomic():
                    appliance = Appliance.objects.get(id=appliance_id)
                    if not appliance.is_openshift:
                        appliance.ip_address = current_ip
                    appliance.set_power_state(Appliance.Power.ON)
                    appliance.save()
                if appliance.containerized and not appliance.is_openshift:
                    with appliance.ipapp.ssh_client as ssh:
                        # Fire up the container
                        ssh.run_command('cfme-start', ensure_host=True)
                # VM is running now.
                sync_appliance_hw.delay(appliance.id)
                sync_provider_hw.delay(appliance.template.provider.id)
                # fixes time synchronization
                if not appliance.is_openshift:
                    appliance.ipapp.fix_ntp_clock()
                return
            else:
                # IP not present yet
                Appliance.objects.get(id=appliance_id).set_status("Appliance waiting for IP.")
                self.retry(args=(appliance_id, ), countdown=20, max_retries=40)
        elif not vm_steady:
            # TODO: change after openshift wrapanapi refactor
            if appliance.is_openshift:
                current_state = appliance.provider_api.vm_status(appliance.name)
            else:
                current_state = appliance.vm_mgmt.state
            appliance.set_status("Waiting for appliance to be steady (current state: {}).".format(
                current_state))
            self.retry(args=(appliance_id, ), countdown=20, max_retries=40)
        else:
            appliance.set_status("Powering on.")
            # TODO: change after openshift wrapanapi refactor
            if appliance.is_openshift:
                appliance.provider_api.start_vm(appliance.name)
            else:
                appliance.vm_mgmt.start()
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
        if not appliance.provider.is_working:
            raise RuntimeError('Provider {} is not working.'.format(appliance.provider))
        api = appliance.provider_api
        # TODO: change after openshift wrapanapi refactor
        # we could use vm.ensure_state(VmState.STOPPED) here in future
        vm_exists = False
        if api.does_vm_exist(appliance.name):
            vm_exists = True
            if appliance.is_openshift:
                vm_stopped = api.is_vm_stopped(appliance.name)
                vm_suspended = api.is_vm_suspended(appliance.name)
                vm_steady = api.in_steady_state(appliance.name)
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
                api.start_vm(appliance.name)
            else:
                appliance.vm_mgmt.start()
            self.retry(args=(appliance_id,), countdown=20, max_retries=40)
        elif not vm_steady:
            # TODO: change after openshift wrapanapi refactor
            if appliance.is_openshift:
                vm_status = api.vm_status(appliance.name)
            else:
                vm_status = appliance.vm_mgmt.state
            appliance.set_status("Waiting for appliance to be steady (current state: {}).".format(
                vm_status))
            self.retry(args=(appliance_id,), countdown=20, max_retries=40)
        else:
            appliance.set_status("Powering off.")
            # TODO: change after openshift wrapanapi refactor
            if appliance.is_openshift:
                api.stop_vm(appliance.name)
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
        if appliance.is_openshift:
            vm_suspended = api.is_vm_suspended(appliance.name)
            vm_steady = api.in_steady_state(appliance.name)
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
                vm_status = api.vm_status(appliance.name)
            else:
                vm_status = appliance.vm_mgmt.state
            appliance.set_status("Waiting for appliance to be steady (current state: {}).".format(
                vm_status))
            self.retry(args=(appliance_id,), countdown=20, max_retries=30)
        else:
            appliance.set_status("Suspending.")
            # TODO: change after openshift wrapanapi refactor
            if appliance.is_openshift:
                appliance.provider_api.suspend_vm(appliance.name)
            else:
                appliance.vm_mgmt.suspend()
            self.retry(args=(appliance_id,), countdown=20, max_retries=30)
    except Exception as e:
        provider_error_logger().error("Exception {}: {}".format(type(e).__name__, str(e)))
        self.retry(args=(appliance_id,), exc=e, countdown=20, max_retries=30)


@singleton_task()
def retrieve_appliance_ip(self, appliance_id):
    """Updates appliance's IP address."""
    try:
        appliance = Appliance.objects.get(id=appliance_id)
        if not appliance.provider.is_working:
            raise RuntimeError('Provider {} is not working.'.format(appliance.provider))
        appliance.set_status("Retrieving IP address.")
        # TODO: change after openshift wrapanapi refactor
        if appliance.is_openshift:
            ip_address = appliance.provider_api.current_ip_address(appliance.name)
        else:
            ip_address = appliance.vm_mgmt.ip
        if ip_address is None:
            self.retry(args=(appliance_id,), countdown=30, max_retries=20)
        with transaction.atomic():
            appliance = Appliance.objects.get(id=appliance_id)
            appliance.ip_address = ip_address
            appliance.save(update_fields=['ip_address'])
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
    provider = Provider.objects.get(id=provider_id, working=True, disabled=False)
    if not hasattr(provider.api, "list_vms"):
        # Ignore this provider
        return
    vms = provider.api.list_vms()
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
                vm.state, Appliance.Power.UNKNOWN))
            appliance.save()
        elif appliance.name in dict_vms:
            vm = dict_vms[appliance.name]
            # Using the name, and then retrieve uuid
            appliance.uuid = vm.uuid
            appliance.ip_address = vm.ip
            appliance.set_power_state(Appliance.POWER_STATES_MAPPING.get(
                vm.state, Appliance.Power.UNKNOWN))
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
    for provider in Provider.objects.filter(disabled=False):
        check_templates_in_provider.delay(provider.id)


@singleton_task(soft_time_limit=180)
def check_templates_in_provider(self, provider_id):
    self.logger.info("Initiated a periodic template check for {}".format(provider_id))
    provider = Provider.objects.get(id=provider_id, disabled=False)
    # Get templates and update metadata
    try:
        # TODO: change after openshift wrapanapi refactor
        if isinstance(provider.api, Openshift):
            templates = map(str, provider.api.list_template())
        else:
            templates = [tmpl.name for tmpl in provider.api.list_templates()]
    except Exception as err:
        self.logger.warning("Provider %s will be marked as not working because of %s",
                            provider_id, err)
        provider.working = False
        provider.save(update_fields=['working'])
    else:
        self.logger.info("Provider %s will be marked as working", provider_id)
        provider.working = True
        provider.save(update_fields=['working'])
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
            tpl.save(update_fields=['exists'])
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
                    appliance.save(update_fields=['appliance_pool'])
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
        self.logger.info(
            "Trying to kill unkilled appliance {}/{}".format(appliance.id, appliance.name))
        Appliance.kill(appliance, force_delete=True)


def generic_shepherd(self, preconfigured):
    """This task takes care of having the required templates spinned into required number of
    appliances. For each template group, it keeps the last template's appliances spinned up in
    required quantity. If new template comes out of the door, it automatically kills the older
    running template's appliances and spins up new ones. Sorts the groups by the fulfillment."""
    for gs in sorted(
            GroupShepherd.objects.all(), key=lambda g: g.get_fulfillment_percentage(preconfigured)):
        prov_filter = {'provider__user_groups': gs.user_group}
        group_versions = Template.get_versions(
            template_group=gs.template_group, ready=True, usable=True, preconfigured=preconfigured,
            **prov_filter)
        group_dates = Template.get_dates(
            template_group=gs.template_group, ready=True, usable=True, preconfigured=preconfigured,
            **prov_filter)
        if group_versions:
            # Downstream - by version (downstream releases)
            version = group_versions[0]
            # Find the latest date (one version can have new build)
            dates = Template.get_dates(
                template_group=gs.template_group, ready=True, usable=True,
                version=group_versions[0], preconfigured=preconfigured, **prov_filter)
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

        filter_keep.update(prov_filter)
        for filt in filters_kill:
            filt.update(prov_filter)
        # Keeping current appliances
        # Retrieve list of all templates for given group
        # I know joins might be a bit better solution but I'll leave that for later.
        possible_templates = list(
            Template.objects.filter(
                usable=True, ready=True, template_group=gs.template_group,
                preconfigured=preconfigured, **filter_keep).all())
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
        pool_size = gs.template_pool_size if preconfigured else gs.unconfigured_template_pool_size
        if len(appliances) < pool_size and possible_templates_for_provision:
            # There must be some templates in order to run the provisioning
            # Provision ONE appliance at time for each group, that way it is possible to maintain
            # reasonable balancing
            with transaction.atomic():
                # Now look for templates that are on non-busy providers
                tpl_free = filter(
                    lambda t: t.provider.free,
                    possible_templates_for_provision)
                if tpl_free:
                    chosen_template = sorted(tpl_free, key=lambda t: t.provider.appliance_load)[0]
                    new_appliance_name = gen_appliance_name(chosen_template.id)
                    appliance = Appliance(
                        template=chosen_template,
                        name=new_appliance_name)
                    appliance.save()
                    self.logger.info(
                        "Adding an appliance to shepherd: {}/{}".format(appliance.id,
                                                                        appliance.name))
                    clone_template_to_appliance.delay(appliance.id, None)
        elif len(appliances) > pool_size:
            # Too many appliances, kill the surplus
            # Only kill those that are visible only for one group. This is necessary so the groups
            # don't "fight"
            for appliance in appliances[:len(appliances) - pool_size]:
                if appliance.is_visible_only_in_group(gs.user_group):
                    self.logger.info("Killing an extra appliance {}/{} in shepherd".format(
                        appliance.id, appliance.name))
                    Appliance.kill(appliance)

        # Killing old appliances
        for filter_kill in filters_kill:
            for template in Template.objects.filter(
                    ready=True, usable=True, template_group=gs.template_group,
                    preconfigured=preconfigured, **filter_kill):

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
        self.logger.info("Waiting for appliance {} to become ready".format(appliance_id))
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
                appliance.save(update_fields=['ready'])
                self.logger.info("Appliance {} became ready".format(appliance_id))
            appliance.set_status("The appliance is ready.")
            with diaper:
                appliance.synchronize_metadata()
        else:
            with transaction.atomic():
                appliance = Appliance.objects.get(id=appliance_id)
                appliance.ready = False
                self.logger.warning("Appliance {} isn't ready yet".format(appliance_id))
                appliance.save(update_fields=['ready'])
            appliance.set_status("Waiting for UI to appear.")
            self.retry(args=(appliance_id,), countdown=30, max_retries=45)
    except ObjectDoesNotExist:
        # source object is not present, terminating
        self.logger.error("Appliance {} isn't present".format(appliance_id))
        return


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


@singleton_task()
def delete_template_from_provider(self, template_id):
    template = Template.objects.get(id=template_id)
    if not template.provider.is_working:
        raise RuntimeError('Provider {} is not working.'.format(template.provider))
    try:
        # TODO: change after openshift wrapanapi refactor
        if isinstance(template.provider.api, Openshift):
            template.provider_api.delete_template(template.name)
        elif template.template_mgmt:
            template.template_mgmt.cleanup()
    except Exception as e:
        self.logger.exception(e)
        return False
    with transaction.atomic():
        template = Template.objects.get(pk=template.pk)
        template.exists = False
        template.save(update_fields=['exists'])
    return True


@singleton_task()
def appliance_rename(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        self.logger.warning("No such appliance {} in sprout".format(appliance_id))
        return None

    if appliance.appliance_pool is None:
        self.logger.info("Appliance {} is shepherd appliance "
                         "and shouldn't be renamed".format(appliance_id))
        return None

    if not appliance.provider.is_working:
        raise RuntimeError('Provider {} is not working.'.format(appliance.provider))
    if (not appliance.provider.allow_renaming or appliance.is_openshift or
            not hasattr(appliance.vm_mgmt, 'rename')):
        self.logger.info("Appliance {} cannot be renamed".format(appliance_id))
        return None

    new_name = '{}_'.format(appliance.appliance_pool.owner.username)
    if appliance.version and not appliance.version.startswith('...'):
        # CFME
        new_name += 'cfme_{}_'.format(appliance.version.replace('.', ''))
    else:
        # MIQ
        new_name += 'miq_'
    new_name += '{}_{}'.format(
        appliance.template.date.strftime("%y%m%d"),
        fauxfactory.gen_alphanumeric(length=4))
    self.logger.info("Start renaming process for {} to {}".format(appliance_id, new_name))

    if appliance.name == new_name:
        self.logger.info("Appliance {} already has such name".format(appliance_id))
        return None

    with redis.appliances_ignored_when_renaming(appliance.name, new_name):
        self.logger.info("Renaming {}/{} to {}".format(appliance_id, appliance.name, new_name))
        appliance.vm_mgmt.rename(new_name)
        appliance.name = new_name
        appliance.save(update_fields=['name'])
    return appliance.name


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
        managed_providers = appliance.ipapp.managed_known_providers
        appliance.managed_providers = [prov.key for prov in managed_providers]
    except Exception as e:
        # To prevent single appliance messing up whole result
        provider_error_logger().error("{}: {}".format(type(e).__name__, str(e)))
        return None
    return appliance.id


@singleton_task()
def calculate_provider_management_usage(self, appliance_ids):
    results = {}
    for appliance_id in filter(lambda id: id is not None, appliance_ids):
        try:
            appliance = Appliance.objects.get(id=appliance_id)
        except ObjectDoesNotExist:
            # Deleted in meanwhile
            continue
        for provider_key in appliance.managed_providers:
            if provider_key not in results:
                results[provider_key] = []
            results[provider_key].append(appliance.id)
    for provider in Provider.objects.filter(working=True, disabled=False):
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
        result = send_mail(
            "Template version mismatches detected",
            email_body,
            "sprout-template-version-mismatch@example.com",
            ['cfme-qe-infra@redhat.com'],
        )
        if result > 0:
            for mismatch in mismatches:
                mismatch.sent = True
                mismatch.save(update_fields=['sent'])


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
            appliance.save()
        return True


@singleton_task()
def disconnect_direct_lun(self, appliance_id):
    self.logger.info("Disconnect direct lun has been started for {}".format(appliance_id))
    appliance = Appliance.objects.get(id=appliance_id)
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
            appliance.save()
        return True


@singleton_task()
def appliance_yum_update(self, appliance_id):
    appliance = Appliance.objects.get(id=appliance_id)
    appliance.ipapp.update_rhel(reboot=False)


@singleton_task()
def appliance_set_hostname(self, appliance_id):
    appliance = Appliance.objects.get(id=appliance_id)
    if appliance.provider.provider_data.get('type', None) == 'openstack':
        appliance.ipapp.set_resolvable_hostname()


@singleton_task()
def appliance_set_ansible_url(self, appliance_id):
    appliance = Appliance.objects.get(id=appliance_id)
    if appliance.is_openshift and Version(appliance.version) >= '5.10':
        appliance.cfme.set_ansible_url()


@singleton_task()
def pick_templates_for_deletion(self):
    """Applies some heuristics to guess templates that might be candidates to deletion."""
    to_mail = {}
    for group in Group.objects.all():
        for zstream, versions in group.pick_versions_to_delete().items():
            for version in versions:
                for template in Template.objects.filter(
                        template_group=group, version=version, exists=True, suggested_delete=False):
                    template.suggested_delete = True
                    template.save(update_fields=['suggested_delete'])
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
            ready=True, power_state=Appliance.Power.ON,
            marked_for_deletion=False).exclude(power_state=Appliance.Power.ORPHANED):
        if appliance.is_openshift:
            continue
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
    for user, messages in per_user.items():
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
        try:
            appliance.synchronize_metadata()
        except ObjectDoesNotExist:
            return


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
    provider = Provider.objects.get(id=provider_id, working=True, disabled=False)
    provider_api = provider.api
    if not hasattr(provider_api, 'list_vms'):
        # This provider does not have VMs
        return
    for vm in sorted(provider_api.list_vms()):
        if Appliance.objects.filter(name=vm.name, template__provider=provider).count() != 0:
            continue
        # We have an untracked VM. Let's investigate
        try:
            appliance_id = vm.get_meta_value('sprout_id')
        except KeyError:
            continue
        except (AttributeError, NotImplementedError):
            # Do not bother if not implemented in the VM object's API
            return

        # just check it again ...
        if Appliance.objects.filter(id=appliance_id).count() == 1:
            # For some reason it is already in
            continue

        # Now it appears that this is a VM that was in Sprout
        construct = {'id': appliance_id}
        # Retrieve appliance data
        try:
            self.logger.info('Trying to reconstruct appliance %d/%s', appliance_id, vm.name)
            construct['name'] = vm.name
            template_id = vm.get_meta_value('sprout_source_template_id')
            # Templates are not deleted from the DB so this should be OK.
            construct['template'] = Template.objects.get(id=template_id)
            construct['name'] = vm.name
            construct['ready'] = vm.get_meta_value('sprout_ready')
            construct['description'] = vm.get_meta_value('sprout_description')
            construct['lun_disk_connected'] = vm.get_meta_value('sprout_lun_disk_connected')
            construct['swap'] = vm.get_meta_value('sprout_swap')
            construct['ssh_failed'] = vm.get_meta_value('sprout_ssh_failed')
            # Time fields
            construct['datetime_leased'] = parsedate(vm.get_meta_value('sprout_datetime_leased'))
            construct['leased_until'] = parsedate(vm.get_meta_value('sprout_leased_until'))
            construct['status_changed'] = parsedate(vm.get_meta_value('sprout_status_changed'))
            construct['created_on'] = parsedate(vm.get_meta_value('sprout_created_on'))
            construct['modified_on'] = parsedate(vm.get_meta_value('sprout_modified_on'))
        except KeyError as e:
            self.logger.error('Failed to reconstruct %d/%s', appliance_id, vm.name)
            self.logger.exception(e)
            continue
        # Retrieve pool data if applicable
        try:
            pool_id = vm.get_meta_value('sprout_pool_id')
            pool_construct = {'id': pool_id}
            pool_construct['total_count'] = vm.get_meta_value('sprout_pool_total_count')
            group_id = vm.get_meta_value('sprout_pool_group')
            pool_construct['group'] = Group.objects.get(id=group_id)
            try:
                construct_provider_id = vm.get_meta_value('sprout_pool_provider')
                pool_construct['provider'] = Provider.objects.get(id=construct_provider_id)
            except (KeyError, ObjectDoesNotExist):
                # optional
                pool_construct['provider'] = None
            pool_construct['version'] = vm.get_meta_value('sprout_pool_version')
            pool_construct['date'] = parsedate(vm.get_meta_value('sprout_pool_appliance_date'))
            owner_id = vm.get_meta_value('sprout_pool_owner_id')
            try:
                owner = User.objects.get(id=owner_id)
            except ObjectDoesNotExist:
                owner_username = vm.get_meta_value('sprout_pool_owner_username')
                owner = User(id=owner_id, username=owner_username)
                owner.save()
            pool_construct['owner'] = owner
            pool_construct['preconfigured'] = vm.get_meta_value('sprout_pool_preconfigured')
            pool_construct['description'] = vm.get_meta_value('sprout_pool_description')
            pool_construct['not_needed_anymore'] = vm.get_meta_value(
                'sprout_pool_not_needed_anymore')
            pool_construct['finished'] = vm.get_meta_value('sprout_pool_finished')
            pool_construct['yum_update'] = vm.get_meta_value('sprout_pool_yum_update')
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


@singleton_task()
def read_docker_images_from_url(self):
    for group in Group.objects.exclude(Q(templates_url=None) | Q(templates_url='')):
        read_docker_images_from_url_group.delay(group.id)


@singleton_task()
def read_docker_images_from_url_group(self, group_id):
    group = Group.objects.get(id=group_id)
    with closing(urlopen(group.templates_url)) as http:
        root = etree.parse(http, parser=etree.HTMLParser()).getroot()

    result = set()
    for link in root.xpath('//a[../../td/img[contains(@src, "folder")]]'):
        try:
            href = link.attrib['href']
        except KeyError:
            continue
        url = group.templates_url + href
        version_with_suffix = href.rstrip('/')  # Does not contain the last digit
        try:
            with closing(urlopen(url + 'cfme-docker')) as http:
                cfme_docker = http.read().strip()
        except HTTPError:
            self.logger.info('Skipping {} (no docker)'.format(url))
            continue

        try:
            with closing(urlopen(url + 'version')) as http:
                cfme_version = http.read().strip()
                if '-' in version_with_suffix:
                    # Use the suffix from the folder name
                    suffix = version_with_suffix.rsplit('-', 1)[-1]
                    cfme_version = '{}-{}'.format(cfme_version, suffix)
        except HTTPError:
            self.logger.info('Skipping {} (no version)'.format(url))
            continue

        cfme_docker = re.split(r'\s+', cfme_docker)
        if len(cfme_docker) == 2:
            pull_url, latest_mapping = cfme_docker
            latest = re.sub(r'^\(latest=([^)]+)\)$', '\\1', latest_mapping)
            proper_pull_url = re.sub(r':latest$', ':{}'.format(latest), pull_url)
        elif cfme_docker and cfme_docker[0].lower().strip() == 'tags:':
            # Multiple tags, take the longest
            proper_pull_url = sorted(filter(None, cfme_docker[1:]), key=len, reverse=True)[0]
            latest = proper_pull_url.rsplit(':', 1)[-1]
        else:
            self.logger.info('Skipping: unknown format: {!r}'.format(cfme_docker))
            continue
        if cfme_version in result:
            continue
        process_docker_images_from_url_group.delay(group.id, cfme_version, latest, proper_pull_url)
        result.add(cfme_version)


@singleton_task()
def process_docker_images_from_url_group(self, group_id, version, docker_version, pull_url):
    group = Group.objects.get(id=group_id)
    # "-20160624221308"
    date = docker_version.rsplit('-', 1)[-1]
    try:
        date = datetime.strptime(date, '%Y%m%d%H%M%S').date()  # noqa
    except AttributeError:
        raise ValueError('Could not parse date from {}'.format(docker_version))
    if group.template_obsolete_days is not None:
        today = datetime.now().date()
        age = today - date
        if age > group.template_obsolete_days:
            self.logger.info('Ignoring old template {} (age {} days)'.format(pull_url, age))
            return
    for provider in Provider.objects.filter(working=True, disabled=False):
        if not provider.container_base_template:
            # 11:30 PM, TODO put this check in a query
            continue
        if provider.remaining_configuring_slots < 1:
            # Will do it later ...
            continue
        if provider.provider_type == 'openshift':
            # openshift providers aren't containerized ones
            continue
        try:
            Template.objects.get(
                ~Q(container=None), template_group=group, provider=provider, version=version,
                date=date, preconfigured=True)
        except ObjectDoesNotExist:
            create_docker_vm.delay(group.id, provider.id, version, date, pull_url)


def docker_vm_name(version, date):
    return 'docker-{}-{}-{}'.format(
        re.sub(r'[^0-9a-z]', '', version.lower()),
        re.sub(r'[^0-9]', '', str(date)),
        fauxfactory.gen_alphanumeric(length=4).lower())


@singleton_task()
def create_docker_vm(self, group_id, provider_id, version, date, pull_url):
    group = Group.objects.get(id=group_id)
    provider = Provider.objects.get(id=provider_id, working=True, disabled=False)
    with transaction.atomic():
        if provider.remaining_configuring_slots < 1:
            self.retry(
                args=(group_id, provider_id, version, date, pull_url), countdown=60, max_retries=60)

        new_name = docker_vm_name(version, date)
        new_template = Template(
            template_group=group, provider=provider,
            container='cfme', name=new_name, original_name=provider.container_base_template,
            version=version, date=date,
            ready=False, exists=False, usable=True, preconfigured=True,
            template_type=Template.DOCKER_VM)
        new_template.save()

    workflow = chain(
        prepare_template_deploy.si(new_template.id),
        configure_docker_template.si(new_template.id, pull_url),
        prepare_template_seal.si(new_template.id),
        prepare_template_poweroff.si(new_template.id),
        prepare_template_finish.si(new_template.id),
    )
    workflow.link_error(prepare_template_delete_on_error.si(new_template.id))
    workflow()


@singleton_task()
def configure_docker_template(self, template_id, pull_url):
    template = Template.objects.get(id=template_id)
    template.set_status("Waiting for SSH.")
    appliance = CFMEAppliance.from_provider(
        template.provider_name, template.name, container=template.container)
    appliance.ipapp.wait_for_ssh()
    with appliance.ipapp.ssh_client as ssh:
        template.set_status("Setting the pull URL.")
        ssh.run_command(
            'echo "export CFME_URL={}" > /etc/cfme_pull_url'.format(pull_url), ensure_host=True)
        template.set_status("Pulling the {}.".format(pull_url))
        ssh.run_command('docker pull {}'.format(pull_url), ensure_host=True)
        template.set_status('Pulling finished.')


@singleton_task()
def sync_appliance_hw(self, appliance_id):
    Appliance.objects.get(id=appliance_id).sync_hw()


@singleton_task()
def sync_provider_hw(self, provider_id):
    Provider.objects.get(id=provider_id, working=True, disabled=False).perf_sync()


@singleton_task()
def sync_quotas_perf(self):
    for provider in Provider.objects.all():
        sync_provider_hw.delay(provider.id)
        for appliance in provider.currently_managed_appliances:
            sync_appliance_hw.delay(appliance.id)


@singleton_task()
def nuke_template_configuration(self, template_id):
    try:
        template = Template.objects.get(id=template_id)
    except ObjectDoesNotExist:
        # No longer exists
        return True

    if template.provider.api.does_vm_exist(template.name):
        self.logger.info('Found the template as a VM')
        # TODO: change after openshift wrapanapi refactor
        if isinstance(template.provider.api, Openshift):
            template.provider.api.delete_vm(template.name)
        elif template.vm_mgmt:
            template.vm_mgmt.cleanup()
    if template.provider.api.does_template_exist(template.name):
        self.logger.info('Found the template as a template')
        # TODO: change after openshift wrapanapi refactor
        if isinstance(template.provider.api, Openshift):
            template.provider.api.delete_template(template.name)
        elif template.template_mgmt:
            template.template_mgmt.cleanup()
    template.delete()
    return True
