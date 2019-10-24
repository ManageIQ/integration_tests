import random
import re
from contextlib import closing
from datetime import datetime
from urllib.error import HTTPError
from urllib.request import urlopen

import diaper
import fauxfactory
import yaml
from celery import chain
from celery.exceptions import MaxRetriesExceededError
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from lxml import etree
from miq_version import Version
from novaclient.exceptions import OverLimit as OSOverLimit
from wait_for import TimedOutError

from cfme.utils.appliance import Appliance as CFMEAppliance
from cfme.utils.net import wait_pingable
from cfme.utils.wait import wait_for
from . import (docker_vm_name, logged_task, singleton_task, provider_error_logger,
               gen_appliance_name)
from .service_ops import appliance_power_on, appliance_yum_update, kill_appliance, appliance_reboot
from .template import (prepare_template_deploy, prepare_template_seal, prepare_template_poweroff,
                       prepare_template_finish, prepare_template_delete_on_error)
from appliances.models import (Provider, Group, Template, Appliance, AppliancePool,
                               DelayedProvisionTask, GroupShepherd)
from sprout import redis


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
def clone_template_to_appliance(self, appliance_id, lease_time_minutes=None, yum_update=False):
    appliance = Appliance.objects.get(id=appliance_id)
    appliance.set_status("Beginning deployment process")
    tasks = [
        clone_template_to_appliance__clone_template.si(appliance_id, lease_time_minutes),
        clone_template_to_appliance__wait_present.si(appliance_id),
        appliance_rename.si(appliance_id),
        appliance_power_on.si(appliance_id),
        retrieve_appliance_ip.si(appliance_id),
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
                kwargs['tags'] = yaml.safe_load(appliance.template.custom_data).get('TAGS')

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
        from .maintainance import refresh_appliances_provider
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


@logged_task()
def clone_template(self, template_id):
    self.logger.info("Cloning template {}".format(template_id))
    template = Template.objects.get(id=template_id)
    new_appliance_name = gen_appliance_name(template_id)
    appliance = Appliance(template=template, name=new_appliance_name)
    appliance.save()
    clone_template_to_appliance.delay(appliance.id)


def clone_template_to_pool(template_id, appliance_pool_id, time_minutes):
    template = Template.objects.get(id=template_id)
    with transaction.atomic():
        pool = AppliancePool.objects.get(id=appliance_pool_id)
        if pool.not_needed_anymore:
            return

        new_appliance_name = gen_appliance_name(template_id, username=pool.owner.username)
        appliance = Appliance(template=template, name=new_appliance_name, appliance_pool=pool)
        appliance.save()
        appliance.set_lease_time()
        # Set pool to these params to keep the appliances with same versions/dates
        pool.version = template.version
        pool.date = template.date
        pool.save(update_fields=['version', 'date'])
    clone_template_to_appliance.delay(appliance.id, time_minutes, pool.yum_update)


@logged_task()
def replace_clone_to_pool(
        self, version, date, appliance_pool_id, time_minutes, exclude_template_id):
    appliance_pool = AppliancePool.objects.get(id=appliance_pool_id)
    if appliance_pool.not_needed_anymore:
        return
    exclude_template = Template.objects.get(id=exclude_template_id)
    templates = appliance_pool.possible_templates
    templates_excluded = [tpl for tpl in templates if tpl != exclude_template]
    if templates_excluded:
        template = random.choice(templates_excluded)
    else:
        template = exclude_template  # :( no other template to use
    clone_template_to_pool(template.id, appliance_pool_id, time_minutes)


@singleton_task()
def apply_lease_times_after_pool_fulfilled(self, appliance_pool_id, time_minutes):
    try:
        pool = AppliancePool.objects.get(id=appliance_pool_id)
    except ObjectDoesNotExist as e:
        self.logger.error("It seems such appliance pool %s doesn't exist: %s", appliance_pool_id,
                          str(e))
        return False

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


@logged_task()
def apply_lease_times(self, appliance_id, time_minutes):
    self.logger.info(
        "Applying lease time {} minutes on appliance {}".format(time_minutes, appliance_id))
    with transaction.atomic():
        appliance = Appliance.objects.get(id=appliance_id)
        appliance.set_lease_time(time_minutes)
        self.logger.info(
            "Lease time has been applied successfully "
            "on appliance {}, pool {}, provider {}".format(appliance_id,
                                                           appliance.appliance_pool.id,
                                                           appliance.provider_name))


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
        del appliance.vm_mgmt  # its cached and based on appliance VM name
        appliance.save(update_fields=['name'])
    return appliance.name


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
            ip_address, _ = wait_for(
                appliance.provider_api.get_appliance_url,
                func_args=[appliance.name],
                fail_condition=None,
                delay=5,
                num_sec=30,
            )
        else:
            if appliance.vm_mgmt is None:
                self.logger.warning(
                    'Appliance %s vm_mgmt is None, probably appliance is renamed or '
                    'we try retrieving IP on orphaned appliance',
                    appliance_id
                )
                self.retry(args=(appliance_id,), countdown=2, max_retries=10)

            ip_address = wait_pingable(appliance.vm_mgmt)
        self.logger.info('Updating with reachable IP %s for appliance %s',
                         ip_address, appliance_id)

        with transaction.atomic():
            appliance = Appliance.objects.get(id=appliance_id)
            appliance.ip_address = ip_address
            appliance.save(update_fields=['ip_address'])
    except ObjectDoesNotExist:
        # source object is not present, terminating
        self.logger.warning('Appliance object not found for id %s in retrieve_appliance_ip',
                            appliance_id)
        return
    except TimedOutError:
        self.logger.info('No reachable IPs found for appliance %s, retrying', appliance_id)
        self.retry(args=(appliance_id,), countdown=2, max_retries=10)
    else:
        appliance.set_status("appliance {a} IP address retrieved".format(a=appliance_id))


@singleton_task()
def appliance_set_ansible_url(self, appliance_id):
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist as e:
        self.logger.error("It seems such appliance %s doesn't exist: %s", appliance_id, str(e))
        return False
    if appliance.is_openshift and Version(appliance.version) >= '5.10':
        appliance.cfme.set_ansible_url()


@singleton_task()
def appliance_set_hostname(self, appliance_id):
    appliance = Appliance.objects.get(id=appliance_id)
    if appliance.provider.provider_data.get('type', None) == 'openstack':
        appliance.ipapp.set_resolvable_hostname()


@singleton_task()
def mark_appliance_ready(self, appliance_id):
    with transaction.atomic():
        appliance = Appliance.objects.get(id=appliance_id)
        appliance.ready = True
        appliance.save(update_fields=['ready'])
    Appliance.objects.get(id=appliance_id).set_status("Appliance was marked as ready")


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
                self.request.callbacks = None
                kill_appliance.delay(appliance_id)
                return
        if appliance.power_state == Appliance.Power.UNKNOWN or appliance.ip_address is None:
            retrieve_appliance_ip.delay(appliance_id).get()
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
                filtered_tpls = [tpl for tpl in tpls if tpl.provider != task.provider_to_avoid]
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
                            'Freeing some space in provider by '
                            'killing appliance {}/{}'.format(appl.id, appl.name))
                        Appliance.kill(appl)
                        break  # Just one
        else:
            # There was a free appliance in shepherd, so we took it and we don't need this task more
            task.delete()


@singleton_task()
def free_appliance_shepherd(self):
    generic_shepherd(self, True)
    generic_shepherd(self, False)


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
            proper_pull_url = sorted([_f for _f in cfme_docker[1:] if _f], key=len, reverse=True)[0]
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
        if age.days > group.template_obsolete_days:
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
        possible_templates_for_provision = [tpl for tpl in possible_templates if tpl.exists]
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
                tpl_free = [t for t
                            in possible_templates_for_provision
                            if not t.provider.disabled and t.provider.free]
                if tpl_free:
                    chosen_template = sorted(tpl_free, key=lambda t: t.provider.appliance_load)[0]
                    new_appliance_name = gen_appliance_name(chosen_template.id)
                    appliance = Appliance(
                        template=chosen_template,
                        name=new_appliance_name
                    )
                    appliance.save()
                    self.logger.info("Adding an appliance to shepherd: %s/%s",
                                     appliance.id, appliance.name)
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
