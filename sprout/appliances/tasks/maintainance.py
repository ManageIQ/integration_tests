import re
import socket
from collections import namedtuple
from datetime import timedelta

import command
import yaml
from celery import chord
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from paramiko import SSHException
from wrapanapi import Openshift

from . import parsedate, singleton_task, provider_error_logger
from appliances.models import (Provider, Group, Template, Appliance, AppliancePool,
                               MismatchVersionMailer, User)
from cfme.utils.path import project_path
from sprout import settings, redis
from sprout.irc_bot import send_message


@singleton_task()
def appliances_synchronize_metadata(self):
    for appliance in Appliance.objects.all():
        try:
            appliance.synchronize_metadata()
        except ObjectDoesNotExist:
            return


@singleton_task()
def sync_quotas_perf(self):
    for provider in Provider.objects.all():
        sync_provider_hw.delay(provider.id)
        for appliance in provider.currently_managed_appliances:
            sync_appliance_hw.delay(appliance.id)


@singleton_task()
def sync_provider_hw(self, provider_id):
    self.logger.info("Syncing provider %s hw", provider_id)
    try:
        provider = Provider.objects.get(id=provider_id, working=True, disabled=False)
    except ObjectDoesNotExist:
        self.logger.warning("Provider %s doesn't exist or disabled", provider_id)
        return

    provider.perf_sync()


@singleton_task()
def sync_appliance_hw(self, appliance_id):
    Appliance.objects.get(id=appliance_id).sync_hw()


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


@singleton_task()
def synchronize_untracked_vms_in_provider(self, provider_id):
    """'re'-synchronizes any vms that might be lost during outages."""
    provider = Provider.objects.get(id=provider_id, working=True, disabled=False)
    provider_api = provider.api
    if not hasattr(provider_api, 'list_vms'):
        # This provider does not have VMs
        return
    for vm in sorted(provider_api.list_vms(), key=lambda pvm: getattr(pvm, 'name', pvm)):
        if (
                Appliance.objects.filter(name=getattr(vm, 'name', vm),
                                         template__provider=provider).count() != 0
        ):
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
            pool_construct = dict(id=pool_id)
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
        except KeyError:
            pass

        appliance = Appliance(**construct)
        appliance.save()

        # And now, refresh!
        refresh_appliances_provider.delay(provider.id)


@singleton_task()
def synchronize_untracked_vms(self):
    for provider in Provider.objects.filter(working=True, disabled=False):
        synchronize_untracked_vms_in_provider.delay(provider.id)


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
    for user, messages in list(per_user.items()):
        appliance_list = '\n'.join(['* {}'.format(m) for m in messages])
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

    went_up = ((appliance.swap is not None and
                swap_amount is not None and
                swap_amount > appliance.swap) or
               (appliance.swap is None and
                swap_amount is not None and swap_amount > 0))

    ssh_failed_changed = ssh_failed and not appliance.ssh_failed

    appliance.swap = swap_amount
    appliance.ssh_failed = ssh_failed
    appliance.save(update_fields=['swap', 'ssh_failed'])

    # Returns a tuple - (appliance_id, went_up?, current_amount, ssh_failed?)
    return appliance.id, went_up, swap_amount, ssh_failed_changed


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
def pick_templates_for_deletion(self):
    """Applies some heuristics to guess templates that might be candidates to deletion."""
    to_mail = {}
    for group in Group.objects.all():
        for zstream, versions in list(group.pick_versions_to_delete().items()):
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
def calculate_provider_management_usage(self, appliance_ids):
    results = {}
    for appliance_id in [id for id in appliance_ids if id is not None]:
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


@singleton_task(soft_time_limit=20, time_limit=30)
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
def scavenge_managed_providers(self):
    chord_tasks = []
    for appliance in Appliance.objects.exclude(appliance_pool=None):
        if ((appliance.expires_in == 'never' or
             (isinstance(appliance.expires_in, int, float) and appliance.expires_in > 7200)) and
                appliance.ready and appliance.ip_address):
            chord_tasks.append(scavenge_managed_providers_from_appliance.si(appliance.id))
    chord(chord_tasks)(calculate_provider_management_usage.s())


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


@singleton_task(soft_time_limit=180)
def check_templates_in_provider(self, provider_id):
    self.logger.info("Initiated a periodic template check for {}".format(provider_id))
    provider = Provider.objects.get(id=provider_id, disabled=False)
    # Get templates and update metadata
    try:
        # TODO: change after openshift wrapanapi refactor
        if isinstance(provider.api, Openshift):
            templates = list(map(str, provider.api.list_template()))
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


@singleton_task()
def check_templates(self):
    self.logger.info("Initiated a periodic template check")
    for provider in Provider.objects.filter(disabled=False):
        check_templates_in_provider.delay(provider.id)


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
    FakeVm = namedtuple('FakeVm', ['ip', 'name', 'uuid', 'state'])

    for vm in vms:
        try:
            if provider.provider_type == 'openshift':
                if not provider.api.is_appliance(vm):
                    # there are some service projects in openshift which we need to skip here
                    continue

                vm_data = dict(ip=provider.api.get_appliance_url(vm),
                               name=vm,
                               uuid=provider.api.get_appliance_uuid(vm),
                               state=provider.api.vm_status(vm))
                vm = FakeVm(**vm_data)

            dict_vms[vm.name] = vm
            if vm.uuid:
                uuid_vms[vm.uuid] = vm
        except Exception as e:
            self.logger.error("Couldn't refresh vm {} because of {}".format(vm.name, e.message))
            continue

    for appliance in Appliance.objects.filter(template__provider=provider):
        if appliance.uuid is not None and appliance.uuid in uuid_vms:
            vm = uuid_vms[appliance.uuid]
            # Using the UUID and change the name if it changed
            appliance.name = vm.name
            appliance.set_power_state(Appliance.POWER_STATES_MAPPING.get(
                vm.state, Appliance.Power.UNKNOWN))
        elif appliance.name in dict_vms:
            vm = dict_vms[appliance.name]
            # Using the name, and then retrieve uuid
            appliance.uuid = vm.uuid
            appliance.set_power_state(Appliance.POWER_STATES_MAPPING.get(
                vm.state, Appliance.Power.UNKNOWN))
            self.logger.info("Retrieved UUID for appliance {}/{}: {}".format(
                appliance.id, appliance.name, appliance.uuid))
        else:
            # Orphaned :(
            appliance.set_power_state(Appliance.Power.ORPHANED)
        with transaction.atomic():
            appliance.save()
        appliance.set_status('Appliance Refreshed')


@singleton_task()
def refresh_appliances(self):
    """Dispatches the appliance refresh process among the providers"""
    self.logger.info("Initiating regular appliance provider refresh")
    for provider in Provider.objects.filter(working=True, disabled=False):
        refresh_appliances_provider.delay(provider.id)


@singleton_task()
def remove_empty_appliance_pools(self):
    """There are sometimes empty lost pools. this task is going to remote such lost pools """
    for pool in [pool for pool in AppliancePool.objects.all() if pool.broken_with_no_appliances]:
        try:
            self.logger.info("Removing empty pool id: {}".format(pool.id))
            pool.delete()
        except Exception as e:
            self.logger.exception("Can't delete pool id {} because of {} ".format(pool.id, e))


@singleton_task()
def kill_lost_appliance(self, provider_id, vm_name):
    """Removes passed vm on provider"""
    try:
        self.logger.info("killing vm {} on provider {}".format(vm_name, provider_id))
        provider = Provider.objects.get(id=provider_id)
        if provider.provider_type != 'openshift':
            vm = provider.api.get_vm(vm_name)
            vm.stop()
            vm.delete()
        else:
            provider.api.delete_vm(vm_name)
    except Exception as e:
        self.retry(args=(provider_id, vm_name), exc=e, countdown=30, max_retries=5)


@singleton_task()
def kill_lost_appliances_per_provider(self, provider_id):
    """Looks for lost appliance in some certain provider"""
    rules = settings.CLEANUP_RULES
    provider = Provider.objects.get(id=provider_id)
    self.logger.info("obtaining list of vms on provider {}".format(provider.id))
    try:
        vms = provider.api.list_vms()
        if provider.provider_type == 'openshift':
            vm_names = vms
        else:
            vm_names = []
            for vm in vms:
                try:
                    vm_names.append(vm.name)
                except Exception as e:
                    self.logger.exception("Couldn't get one prov's vm: {p} "
                                          "because of exception {e}".format(p=provider_id,
                                                                            e=e))
                    continue
        # skipping appliances present in sprout db. those will be handled by another task
        vm_names = [name for name in vm_names
                    if not Appliance.objects.filter(name=name, template__provider=provider)]
        # checking vm time
        for rule in rules:
            expiration_time = timezone.now() - timedelta(**rule['lifetime'])
            for name in vm_names:
                if not re.match(rule['name'], name):
                    continue

                if provider.provider_type != 'openshift':
                    try:
                        vm_creation_time = provider.api.get_vm(name).creation_time
                    except Exception as e:
                        self.logger.exception("Couldn't get vm {vm} timestamp (prov: {p}) "
                                              "because of exception {e}".format(vm=name,
                                                                                p=provider_id,
                                                                                e=e))
                        continue
                else:
                    vm_creation_time = provider.api.vm_creation_time(name)

                if vm_creation_time > expiration_time:
                    continue

                # looks like vm matches all rule and can be killed
                kill_lost_appliance.delay(provider.id, name)
    except Exception as e:
        self.logger.exception("exception occurred during obtaining list of vms "
                              "on provider {}".format(provider_id))
        self.logger.exception(e)
        self.retry(args=(), exc=e, countdown=10, max_retries=5)


@singleton_task()
def kill_lost_appliances(self):
    """Looks for lost appliances present on sprout provider and kills them"""
    self.logger.info("looking for old lost vms on sprout providers")
    for provider in Provider.objects.filter(disabled=False, working=True, appliance_limit__gt=0):
        kill_lost_appliances_per_provider.delay(provider.id)


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
                self.logger.info("orphaned appliance {} power "
                                 "state has been changed".format(appliance.id))
                continue
            self.logger.info(
                "I will delete orphaned "
                "appliance {}/{} on provider {}".format(appliance.id, appliance.name,
                                                        appliance.provider.id))
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
            self.logger.info("Killing broken appliance {}/{} "
                             "on provider {}".format(appliance.id, appliance.name,
                                                     appliance.provider.id))
            Appliance.kill(appliance)  # Use kill because the appliance may still exist
    # And now - if something happened during appliance deletion, call kill again
    for appliance in Appliance.objects.filter(
            marked_for_deletion=True, status_changed__lt=expiration_time).all():
        self.logger.info(
            "Trying to kill unkilled appliance {}/{} "
            "on provider {}".format(appliance.id, appliance.name, appliance.provider.id))
        Appliance.kill(appliance, force_delete=True)


@singleton_task()
def kill_expired_appliances(self):
    """This is the watchdog, that guards the appliances that were given to users. If you forget
    to prolong the lease time, this is the thing that will take the appliance off your hands
    and kill it."""
    from .service_ops import kill_appliance
    with transaction.atomic():
        for appliance in Appliance.objects.filter(marked_for_deletion=False):
            if appliance.leased_until is not None and appliance.leased_until <= timezone.now():
                self.logger.info("Watchdog found an appliance that is to be deleted: {}/{}".format(
                    appliance.id, appliance.name))
                kill_appliance.delay(appliance.id)
