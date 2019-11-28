from datetime import timedelta

import fauxfactory
import yaml
from celery import chain
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from miq_version import TemplateName, Version
from wrapanapi import Openshift, VmState, VMWareSystem

from . import logged_task, singleton_task
from appliances.models import Provider, Group, Template, Appliance, MismatchVersionMailer

from cfme.utils import conf
from cfme.utils.appliance import Appliance as CFMEAppliance
from cfme.utils.timeutil import parsetime
from cfme.utils.trackerbot import depaginate, api
from cfme.utils.wait import wait_for

from sprout import settings

TRACKERBOT_PAGINATE = 100


def trackerbot():
    return api(trackerbot_url=settings.HUBBER_URL.rstrip('/') + '/api/')


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
                            exists=False,
                            custom_data='{}')
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
        from .maintainance import mailer_version_mismatch
        mailer_version_mismatch.delay()
        raise Exception("Detected version mismatch!")
    template.set_status("Version verification is over")


@singleton_task()
def prepare_template_configure(self, template_id):
    template = Template.objects.get(id=template_id)
    template.set_status("Customization started.")
    appliance = CFMEAppliance.from_provider(
        template.provider_name, template.name, container=template.container)
    try:
        appliance.configure(
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

        if isinstance(template.provider_api, VMWareSystem):
            # virtualcenter may want to store templates on different datastore
            # migrate if necessary
            host = (template.provider.provider_data.get('template_upload', {}).get('host') or
                    template.provider_api.list_host().pop())
            datastore = template.provider.provider_data.get('template_upload',
                                                            {}).get('template_datastore')
            if host is not None and datastore is not None:
                template.set_status("Migrating VM before mark_as_template for vmware")
                template.vm_mgmt.clone(
                    vm_name=template.name,
                    datastore=datastore,
                    host=host,
                    relocate=True
                )
        # TODO: change after openshift wrapanapi refactor
        # mark the template from the vm or system api
        getattr(
            template,
            'provider_api' if isinstance(template.provider_api, Openshift) else 'vm_mgmt'
        ).mark_as_template(template.name, delete_on_error=True)

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
    for group in list(per_group.keys()):
        per_group[group] = sorted(
            per_group[group],
            reverse=True, key=lambda o: o["template"]["datestamp"])
    objects = []
    # And interleave the the groups
    while any(per_group.values()):
        for key in list(per_group.keys()):
            if per_group[key]:
                objects.append(per_group[key].pop(0))
    for template in objects:
        if template["provider"]["key"] not in list(conf.cfme_data.management_systems.keys()):
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
        if conf.cfme_data.management_systems.get(template["provider"]["key"], {}).get(
                "use_for_sprout", False
        ):  # only create provider in db if it is marked to use for sprout
            provider, create = Provider.objects.get_or_create(id=template["provider"]["key"])
        else:
            continue
        if not provider.is_working:
            continue
        if "sprout" not in provider.provider_data:
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

                # openshift has two templates bound to one build version
                # sometimes sprout tries using second template -extdb that's wrong
                # so, such template has to be marked as not usable inside sprout
                usable = not template_name.endswith('-extdb')
                with transaction.atomic():
                    tpl = Template(
                        provider=provider, template_group=group, original_name=template_name,
                        name=template_name, preconfigured=False, date=template_info.datestamp,
                        ready=True, exists=True, usable=usable, version=template_version)
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
        if conf.cfme_data.management_systems.get(provider_id, {}).get(
                "use_for_sprout", False
        ):  # only create provider in db if it is marked to use for sprout
            provider, create = Provider.objects.get_or_create(id=provider_id)
        else:
            continue
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
                        self.logger.info('Killing an appliance {}/{} '
                                         'because its template was marked '
                                         'as unusable'.format(appliance.id, appliance.name))
                        Appliance.kill(appliance)
