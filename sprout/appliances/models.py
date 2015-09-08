# -*- coding: utf-8 -*-
import yaml

from celery import chain
from contextlib import contextmanager
from datetime import timedelta, date
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.utils import timezone

from sprout import critical_section
from sprout.log import create_logger

from utils import mgmt_system
from utils.appliance import Appliance as CFMEAppliance, IPAppliance
from utils.conf import cfme_data
from utils.providers import get_mgmt
from utils.timeutil import nice_seconds
from utils.version import Version


# Monkey patch the User object in order to have nicer checks
def has_quotas(self):
    try:
        self.quotas
    except ObjectDoesNotExist:
        return False
    else:
        return True

User.has_quotas = property(has_quotas)


def apply_if_not_none(o, meth, *args, **kwargs):
    if o is None:
        return None
    return getattr(o, meth)(*args, **kwargs)


class MetadataMixin(models.Model):
    class Meta:
        abstract = True
    object_meta_data = models.TextField(default=yaml.dump({}))

    def reload(self):
        new_self = self.__class__.objects.get(pk=self.pk)
        self.__dict__.update(new_self.__dict__)

    @property
    @contextmanager
    def metadata_lock(self):
        with critical_section("metadata-({})[{}]".format(self.__class__.__name__, str(self.pk))):
            yield

    @property
    def metadata(self):
        return yaml.load(self.object_meta_data)

    @metadata.setter
    def metadata(self, value):
        if not isinstance(value, dict):
            raise TypeError("You can store only dict in metadata!")
        self.object_meta_data = yaml.dump(value)

    @property
    @contextmanager
    def edit_metadata(self):
        with transaction.atomic():
            with self.metadata_lock:
                o = type(self).objects.get(pk=self.pk)
                metadata = o.metadata
                yield metadata
                o.metadata = metadata
                o.save()
        self.reload()

    @property
    def logger(self):
        return create_logger(self)

    @classmethod
    def class_logger(cls, id=None):
        return create_logger(cls, id)


class DelayedProvisionTask(MetadataMixin):
    pool = models.ForeignKey("AppliancePool")
    lease_time = models.IntegerField(null=True, blank=True)
    provider_to_avoid = models.ForeignKey("Provider", null=True, blank=True)

    def __unicode__(self):
        return u"Task {}: Provision on {}, lease time {}, avoid provider {}".format(
            self.id, self.pool.id, self.lease_time,
            self.provider_to_avoid.id if self.provider_to_avoid is not None else "---")


class Provider(MetadataMixin):
    id = models.CharField(max_length=32, primary_key=True, help_text="Provider's key in YAML.")
    working = models.BooleanField(default=False, help_text="Whether provider is available.")
    num_simultaneous_provisioning = models.IntegerField(default=5,
        help_text="How many simultaneous background provisioning tasks can run on this provider.")
    num_simultaneous_configuring = models.IntegerField(default=1,
        help_text="How many simultaneous template configuring tasks can run on this provider.")
    appliance_limit = models.IntegerField(
        null=True, help_text="Hard limit of how many appliances can run on this provider")

    @property
    def api(self):
        return get_mgmt(self.id)

    @property
    def num_currently_provisioning(self):
        return len(
            Appliance.objects.filter(
                ready=False, marked_for_deletion=False, template__provider=self, ip_address=None))

    @property
    def num_templates_preparing(self):
        return len(Template.objects.filter(provider=self, ready=False))

    @property
    def remaining_configuring_slots(self):
        result = self.num_simultaneous_configuring - self.num_templates_preparing
        if result < 0:
            return 0
        return result

    @property
    def remaining_appliance_slots(self):
        if self.appliance_limit is None:
            return 1
        result = self.appliance_limit - self.num_currently_managing
        if result < 0:
            return 0
        return result

    @property
    def num_currently_managing(self):
        return len(Appliance.objects.filter(template__provider=self))

    @property
    def currently_managed_appliances(self):
        return Appliance.objects.filter(template__provider=self)

    @property
    def remaining_provisioning_slots(self):
        result = self.num_simultaneous_provisioning - self.num_currently_provisioning
        if result < 0:
            return 0
        # Take the appliance limit into account
        if self.appliance_limit is None:
            return result
        else:
            free_appl_slots = self.appliance_limit - self.num_currently_managing
            if free_appl_slots < 0:
                free_appl_slots = 0
            return min(free_appl_slots, result)

    @property
    def free(self):
        return self.remaining_provisioning_slots > 0

    @property
    def provisioning_load(self):
        if self.num_simultaneous_provisioning == 0:
            return 1.0  # prevent division by zero
        return float(self.num_currently_provisioning) / float(self.num_simultaneous_provisioning)

    @property
    def appliance_load(self):
        if self.appliance_limit is None or self.appliance_limit == 0:
            return 0.0
        return float(self.num_currently_managing) / float(self.appliance_limit)

    @property
    def load(self):
        """Load for sorting"""
        if self.appliance_limit is None:
            return self.provisioning_load
        else:
            return self.appliance_load

    @classmethod
    def get_available_provider_keys(cls):
        return cfme_data.get("management_systems", {}).keys()

    @property
    def provider_data(self):
        return cfme_data.get("management_systems", {}).get(self.id, {})

    @property
    def ip_address(self):
        return self.provider_data.get("ipaddress")

    @property
    def templates(self):
        return self.metadata.get("templates", [])

    @templates.setter
    def templates(self, value):
        with self.edit_metadata as metadata:
            metadata["templates"] = value

    @property
    def template_name_length(self):
        return self.metadata.get("template_name_length", None)

    @template_name_length.setter
    def template_name_length(self, value):
        with self.edit_metadata as metadata:
            metadata["template_name_length"] = value

    @property
    def appliances_manage_this_provider(self):
        return self.metadata.get("appliances_manage_this_provider", [])

    @appliances_manage_this_provider.setter
    def appliances_manage_this_provider(self, value):
        with self.edit_metadata as metadata:
            metadata["appliances_manage_this_provider"] = value

    @property
    def g_appliances_manage_this_provider(self):
        for appl_id in self.appliances_manage_this_provider:
            try:
                yield Appliance.objects.get(id=appl_id)
            except ObjectDoesNotExist:
                continue

    @property
    def user_usage(self):
        per_user_usage = {}
        for appliance in Appliance.objects.filter(template__provider=self):
            if appliance.owner is None:
                continue
            owner = appliance.owner.username
            if owner not in per_user_usage:
                per_user_usage[owner] = 1
            else:
                per_user_usage[owner] += 1
        per_user_usage = per_user_usage.items()
        per_user_usage.sort(key=lambda item: item[1], reverse=True)
        return per_user_usage

    @property
    def free_shepherd_appliances(self):
        return Appliance.objects.filter(
            template__provider=self, appliance_pool=None, marked_for_deletion=False, ready=True)

    @classmethod
    def complete_user_usage(cls):
        result = {}
        for provider in cls.objects.all():
            for username, count in provider.user_usage:
                if username not in result:
                    result[username] = 0
                result[username] += count
        result = result.items()
        result.sort(key=lambda item: item[1], reverse=True)
        return result

    def cleanup(self):
        """Put any cleanup tasks that might help the application stability here"""
        self.logger.info("Running cleanup on provider {}".format(self.id))
        if isinstance(self.api, mgmt_system.OpenstackSystem):
            # Openstack cleanup
            # Clean up the floating IPs
            for floating_ip in self.api.api.floating_ips.findall(fixed_ip=None):
                self.logger.info(
                    "Cleaning up the {} floating ip {}".format(self.id, floating_ip.ip))
                try:
                    floating_ip.delete()
                except Exception as e:
                    self.logger.exception(e)

    def vnc_console_link_for(self, appliance):
        if appliance.uuid is None:
            return None
        if isinstance(self.api, mgmt_system.OpenstackSystem):
            return "http://{}/dashboard/project/instances/{}/?tab=instance_details__console".format(
                self.ip_address, appliance.uuid
            )
        else:
            return None

    def __unicode__(self):
        return "{} {}".format(self.__class__.__name__, self.id)


class Group(MetadataMixin):
    id = models.CharField(max_length=32, primary_key=True,
        help_text="Group name as trackerbot says. (eg. upstream, downstream-53z, ...)")
    template_pool_size = models.IntegerField(default=0,
        help_text="How many appliances to keep spinned for quick taking.")
    unconfigured_template_pool_size = models.IntegerField(default=0,
        help_text="How many appliances to keep spinned for quick taking - unconfigured ones.")
    template_obsolete_days = models.IntegerField(
        null=True, blank=True, help_text="Templates older than X days won't be loaded into sprout")
    template_obsolete_days_delete = models.BooleanField(
        default=False,
        help_text="If template_obsolete_days set, this will enable deletion of obsolete templates"
        " using that metric. WARNING! Use with care. Best use for upstream templates.")

    @property
    def obsolete_templates(self):
        """Return a list of obsolete templates. Ignores the latest one even if it was obsolete by
        the means of days."""
        if self.template_obsolete_days is None:
            return None
        latest_template_date = Template.objects.filter(
            exists=True, template_group=self).order_by("-date")[0].date
        latest_template_ids = [
            tpl.id
            for tpl
            in Template.objects.filter(exists=True, template_group=self, date=latest_template_date)]
        return Template.objects.filter(
            exists=True, date__lt=date.today() - timedelta(days=self.template_obsolete_days),
            template_group=self).exclude(id__in=latest_template_ids).order_by("date")

    @property
    def templates(self):
        return Template.objects.filter(template_group=self).order_by("-date", "provider__id")

    @property
    def existing_templates(self):
        return self.templates.filter(exists=True)

    @property
    def appliances(self):
        return Appliance.objects.filter(template__template_group=self)

    def shepherd_appliances(self, preconfigured=True):
        return self.appliances.filter(
            appliance_pool=None, ready=True, marked_for_deletion=False,
            template__preconfigured=preconfigured)

    @property
    def configured_shepherd_appliances(self):
        return self.shepherd_appliances(True)

    @property
    def unconfigured_shepherd_appliances(self):
        return self.shepherd_appliances(False)

    def get_fulfillment_percentage(self, preconfigured):
        """Return percentage of fulfillment of the group shepherd.

        Values between 0-100, can be over 100 if there are more than required.

        Args:
            preconfigured: Whether to check the pure ones or configured ones.
        """
        appliances_in_shepherd = len(
            self.appliances.filter(
                template__preconfigured=preconfigured, appliance_pool=None,
                marked_for_deletion=False))
        wanted_pool_size = (
            self.template_pool_size if preconfigured else self.unconfigured_template_pool_size)
        if wanted_pool_size == 0:
            return 100
        return int(round((float(appliances_in_shepherd) / float(wanted_pool_size)) * 100.0))

    def __unicode__(self):
        return "{} {} (pool size={}/{})".format(
            self.__class__.__name__, self.id, self.template_pool_size,
            self.unconfigured_template_pool_size)


class Template(MetadataMixin):
    provider = models.ForeignKey(Provider, help_text="Where does this template reside")
    template_group = models.ForeignKey(Group, help_text="Which group the template belongs to.")
    version = models.CharField(max_length=16, null=True, help_text="Downstream version.")
    date = models.DateField(help_text="Template build date (original).")

    original_name = models.CharField(max_length=64, help_text="Template's original name.")
    name = models.CharField(max_length=64, help_text="Template's name as it resides on provider.")

    status = models.TextField(default="Template inserted into the system")
    status_changed = models.DateTimeField(auto_now_add=True)
    ready = models.BooleanField(default=False, help_text="Template is ready-to-be-used")
    exists = models.BooleanField(default=True, help_text="Template exists in the provider.")
    usable = models.BooleanField(default=False, help_text="Template is marked as usable")

    preconfigured = models.BooleanField(default=True, help_text="Is prepared for immediate use?")

    @property
    def provider_api(self):
        return self.provider.api

    @property
    def provider_name(self):
        return self.provider.id

    @property
    def exists_in_provider(self):
        return self.name in self.provider_api.list_template()

    def set_status(self, status):
        with transaction.atomic():
            template = Template.objects.get(id=self.id)
            template.status = status
            template.status_changed = timezone.now()
            template.save()
            self.logger.info("{}: {}".format(self.pk, status))

    @property
    def cfme(self):
        return CFMEAppliance(self.provider_name, self.name)

    @property
    def can_be_deleted(self):
        return self.exists and self.preconfigured and len(self.appliances) == 0

    @property
    def appliances(self):
        return Appliance.objects.filter(template=self)

    @property
    def temporary_name(self):
        return self.metadata.get("temporary_name", None)

    @temporary_name.setter
    def temporary_name(self, name):
        with self.edit_metadata as metadata:
            metadata["temporary_name"] = name

    @temporary_name.deleter
    def temporary_name(self):
        with self.edit_metadata as metadata:
            if "temporary_name" in metadata:
                del metadata["temporary_name"]

    @classmethod
    def get_versions(cls, **filters):
        versions = []
        for version in cls.objects.filter(**filters).values('version').distinct():
            v = version.values()[0]
            if v is not None:
                versions.append(v)
        versions.sort(key=Version, reverse=True)
        return versions

    @classmethod
    def get_dates(cls, **filters):
        dates = map(
            lambda d: d.values()[0],
            cls.objects.filter(**filters).values('date').distinct())
        dates.sort(reverse=True)
        return dates

    def __unicode__(self):
        return "{} {}:{} @ {}".format(
            self.__class__.__name__, self.version, self.name, self.provider.id)


class Appliance(MetadataMixin):
    class Power(object):
        ON = "on"
        OFF = "off"
        SUSPENDED = "suspended"
        REBOOTING = "rebooting"
        LOCKED = "locked"
        UNKNOWN = "unknown"
        ORPHANED = "orphaned"

    POWER_STATES_MAPPING = {
        # vSphere
        "poweredOn": Power.ON,
        "poweredOff": Power.OFF,
        "suspended": Power.SUSPENDED,
        # RHEV
        "up": Power.ON,
        "down": Power.OFF,
        "suspended": Power.SUSPENDED,
        "image_locked": Power.LOCKED,
        # Openstack
        "ACTIVE": Power.ON,
        "SHUTOFF": Power.OFF,
        "SUSPENDED": Power.SUSPENDED,
        # SCVMM
        "Running": Power.ON,
        "PoweredOff": Power.OFF,
        "Stopped": Power.OFF,
        "Paused": Power.SUSPENDED,
        # EC2 (for VM manager)
        "stopped": Power.OFF,
        "running": Power.ON,
    }
    template = models.ForeignKey(Template, help_text="Appliance's source template.")
    appliance_pool = models.ForeignKey("AppliancePool", null=True,
        help_text="Which appliance pool this appliance belongs to.")
    name = models.CharField(max_length=64, help_text="Appliance's name as it is in the provider.")
    ip_address = models.CharField(max_length=45, null=True, help_text="Appliance's IP address")

    datetime_leased = models.DateTimeField(null=True, help_text="When the appliance was leased")
    leased_until = models.DateTimeField(null=True, help_text="When does the appliance lease expire")

    status = models.TextField(default="Appliance inserted into the system.")
    status_changed = models.DateTimeField(auto_now_add=True)
    power_state_changed = models.DateTimeField(default=timezone.now)

    marked_for_deletion = models.BooleanField(default=False,
        help_text="Appliance is already being deleted.")

    power_state = models.CharField(max_length=32, default="unknown",
        help_text="Appliance's power state")
    ready = models.BooleanField(default=False,
        help_text="Appliance has an IP address and web UI is online.")
    uuid = models.CharField(max_length=36, null=True, blank=True, help_text="UUID of the machine")
    description = models.TextField(blank=True)
    lun_disk_connected = models.BooleanField(
        default=False,
        help_text="Whether the Direct LUN disk is connected. (RHEV Only)")

    @property
    def serialized(self):
        return dict(
            id=self.id,
            ready=self.ready,
            name=self.name,
            ip_address=self.ip_address,
            status=self.status,
            power_state=self.power_state,
            status_changed=apply_if_not_none(self.status_changed, "isoformat"),
            datetime_leased=apply_if_not_none(self.datetime_leased, "isoformat"),
            leased_until=apply_if_not_none(self.leased_until, "isoformat"),
            template_name=self.template.original_name,
            template_id=self.template.id,
            provider=self.template.provider.id,
            marked_for_deletion=self.marked_for_deletion,
            uuid=self.uuid,
            template_version=self.template.version,
            template_build_date=self.template.date.isoformat(),
            template_group=self.template.template_group.id,
            template_sprout_name=self.template.name,
            preconfigured=self.preconfigured,
            lun_disk_connected=self.lun_disk_connected,
        )

    @property
    @contextmanager
    def kill_lock(self):
        with critical_section("kill-({})[{}]".format(self.__class__.__name__, str(self.pk))):
            yield

    @property
    def provider_api(self):
        return self.template.provider_api

    @property
    def provider_name(self):
        return self.template.provider_name

    @property
    def provider(self):
        return self.template.provider

    @property
    def preconfigured(self):
        return self.template.preconfigured

    @property
    def cfme(self):
        return CFMEAppliance(self.provider_name, self.name)

    @property
    def ipapp(self):
        return IPAppliance(self.ip_address)

    def set_status(self, status):
        with transaction.atomic():
            appliance = Appliance.objects.get(id=self.id)
            if status != appliance.status:
                appliance.status = status
                appliance.status_changed = timezone.now()
                appliance.save()
                self.logger.info("Status changed: {}".format(status))

    def set_power_state(self, power_state):
        if power_state != self.power_state:
            self.logger.info("Changed power state to {}".format(power_state))
            self.power_state = power_state
            self.power_state_changed = timezone.now()

    def __unicode__(self):
        return "{} {} @ {}".format(self.__class__.__name__, self.name, self.template.provider.id)

    @classmethod
    def unassigned(cls):
        return cls.objects.filter(appliance_pool=None, ready=True)

    @classmethod
    def give_to_pool(cls, pool, custom_limit=None):
        """Give appliances from shepherd to the pool where the maximum count is specified by pool
        or you can specify a custom limit
        """
        from appliances.tasks import (
            appliance_power_on, mark_appliance_ready, wait_appliance_ready, appliance_yum_update,
            appliance_reboot)
        limit = custom_limit if custom_limit is not None else pool.total_count
        appliances = []
        with transaction.atomic():
            for template in pool.possible_templates:
                for appliance in cls.unassigned().filter(
                        template=template).all()[:limit - len(appliances)]:
                    with appliance.kill_lock:
                        appliance.appliance_pool = pool
                        appliance.save()
                        appliance.set_status("Given to pool {}".format(pool.id))
                        tasks = [appliance_power_on.si(appliance.id)]
                        if pool.yum_update:
                            tasks.append(appliance_yum_update.si(appliance.id))
                            tasks.append(
                                appliance_reboot.si(appliance.id, if_needs_restarting=True))
                        if appliance.preconfigured:
                            tasks.append(wait_appliance_ready.si(appliance.id))
                        else:
                            tasks.append(mark_appliance_ready.si(appliance.id))
                        chain(*tasks)()
                        appliances.append(appliance)
                if len(appliances) == limit:
                    break
        return len(appliances)

    @classmethod
    def kill(cls, appliance_or_id):
        # Completely delete appliance from provider
        from appliances.tasks import kill_appliance
        if isinstance(appliance_or_id, cls):
            self = Appliance.objects.get(id=appliance_or_id.id)
        else:
            self = Appliance.objects.get(id=appliance_or_id)
        with self.kill_lock:
            with transaction.atomic():
                self = type(self).objects.get(pk=self.pk)
                self.class_logger(self.pk).info("Killing")
                if not self.marked_for_deletion:
                    self.marked_for_deletion = True
                    self.leased_until = None
                    self.save()
                    return kill_appliance.delay(self.id)

    def delete(self, *args, **kwargs):
        # Intercept delete and lessen the number of appliances in the pool
        # Then if the appliance is still present in the management system, kill it
        self.logger.info("Deleting from database")
        pool = self.appliance_pool
        result = super(Appliance, self).delete(*args, **kwargs)
        do_not_touch = kwargs.pop("do_not_touch_ap", False)
        if pool is not None and not do_not_touch:
            if pool.current_count == 0:
                pool.delete()
        return result

    def prolong_lease(self, time=60):
        self.logger.info("Prolonging lease by {} minutes from now.".format(time))
        with transaction.atomic():
            appliance = Appliance.objects.get(id=self.id)
            appliance.leased_until = timezone.now() + timedelta(minutes=time)
            appliance.save()

    @property
    def owner(self):
        if self.appliance_pool is None:
            return None
        else:
            return self.appliance_pool.owner

    @property
    def expires_in(self):
        """Minutes"""
        if self.leased_until is None:
            return "never"
        seconds = (self.leased_until - timezone.now()).total_seconds()
        if seconds <= 0.0:
            return "Expired!"
        else:
            return nice_seconds(seconds)

    @property
    def can_launch(self):
        return self.power_state in {self.Power.OFF, self.Power.SUSPENDED}

    @property
    def can_suspend(self):
        return self.power_state in {self.Power.ON}

    @property
    def can_stop(self):
        return self.power_state in {self.Power.ON}

    @property
    def version(self):
        if self.template.version is None:
            return "---"
        else:
            return self.template.version

    @property
    def managed_providers(self):
        return self.metadata.get("managed_providers", [])

    @managed_providers.setter
    def managed_providers(self, value):
        with self.edit_metadata as metadata:
            metadata["managed_providers"] = value

    @property
    def vnc_link(self):
        try:
            return self.provider.vnc_console_link_for(self)
        except KeyError:  # provider does not exist any more
            return None


class AppliancePool(MetadataMixin):
    total_count = models.IntegerField(help_text="How many appliances should be in this pool.")
    group = models.ForeignKey(Group, help_text="Group which is used to provision appliances.")
    provider = models.ForeignKey(
        Provider, help_text="If requested, appliances can be on single provider.", null=True,
        blank=True)
    version = models.CharField(max_length=16, null=True, help_text="Appliance version")
    date = models.DateField(null=True, help_text="Appliance date.")
    owner = models.ForeignKey(User, help_text="User who owns the appliance pool")

    preconfigured = models.BooleanField(
        default=True, help_text="Whether to provision preconfigured appliances")
    description = models.TextField(blank=True)
    not_needed_anymore = models.BooleanField(
        default=False, help_text="Used for marking the appliance pool as being deleted")
    finished = models.BooleanField(default=False, help_text="Whether fulfillment has been met.")
    yum_update = models.BooleanField(default=False, help_text="Whether to update appliances.")

    @classmethod
    def create(cls, owner, group, version=None, date=None, provider=None, num_appliances=1,
            time_leased=60, preconfigured=True, yum_update=False):
        if owner.has_quotas:
            user_pools_count = cls.objects.filter(owner=owner).count()
            user_vms_count = Appliance.objects.filter(appliance_pool__owner=owner).count()
            if owner.quotas.total_pool_quota is not None:
                if owner.quotas.total_pool_quota <= user_pools_count:
                    raise ValueError(
                        "User has too many pools ({} allowed, {} already existing)".format(
                            owner.quotas.total_pool_quota, user_pools_count))
            if owner.quotas.total_vm_quota is not None:
                if owner.quotas.total_vm_quota <= (user_vms_count + num_appliances):
                    raise ValueError(
                        "Requested {} appliances, limit is {} and currently user has {}".format(
                            num_appliances, owner.quotas.total_vm_quota, user_vms_count))
            if owner.quotas.per_pool_quota is not None:
                if num_appliances > owner.quotas.per_pool_quota:
                    raise ValueError("You are limited to {} VMs per pool, requested {}".format(
                        owner.quotas.per_pool_quota, num_appliances))
        from appliances.tasks import request_appliance_pool
        # Retrieve latest possible
        if not version:
            versions = Template.get_versions(
                template_group=group, ready=True, usable=True, preconfigured=preconfigured,
                provider__working=True)
            if versions:
                version = versions[0]
        if not date:
            if version is not None:
                dates = Template.get_dates(template_group=group, version=version, ready=True,
                    usable=True, preconfigured=preconfigured, provider__working=True)
            else:
                dates = Template.get_dates(
                    template_group=group, ready=True, usable=True, preconfigured=preconfigured,
                    provider__working=True)
            if dates:
                date = dates[0]
        if isinstance(group, basestring):
            group = Group.objects.get(id=group)
        if isinstance(provider, basestring):
            provider = Provider.objects.get(id=provider, working=True)
        if not (version or date):
            raise Exception(
                "Could not find proper combination of group, date, version and a working provider!")
        req = cls(
            group=group, version=version, date=date, total_count=num_appliances, owner=owner,
            provider=provider, preconfigured=preconfigured, yum_update=yum_update)
        if not req.possible_templates:
            raise Exception("No possible templates! (query: {}".format(str(req.__dict__)))
        req.save()
        cls.class_logger(req.pk).info("Created")
        request_appliance_pool.delay(req.id, time_leased)
        return req

    def delete(self, *args, **kwargs):
        self.logger.info("Deleting")
        with transaction.atomic():
            for task in DelayedProvisionTask.objects.filter(pool=self):
                task.delete()

        return super(AppliancePool, self).delete(*args, **kwargs)

    @property
    def filter_params(self):
        filter_params = {
            "template_group": self.group,
            "preconfigured": self.preconfigured,
        }
        if self.version is not None:
            filter_params["version"] = self.version
        if self.date is not None:
            filter_params["date"] = self.date
        if self.provider is not None:
            filter_params["provider"] = self.provider
        return filter_params

    @property
    def appliance_filter_params(self):
        params = self.filter_params
        result = {}
        for key, value in params.iteritems():
            result["template__{}".format(key)] = value
        return result

    @property
    def possible_templates(self):
        return Template.objects.filter(
            ready=True, exists=True, usable=True,
            **self.filter_params).all()

    @property
    def possible_provisioning_templates(self):
        return sorted(
            filter(lambda tpl: tpl.provider.free, self.possible_templates),
            # Sort by date and load to pick the best match (least loaded provider)
            key=lambda tpl: (tpl.date, 1.0 - tpl.provider.appliance_load), reverse=True)

    @property
    def possible_providers(self):
        """Which providers contain a template that could be used for provisioning?."""
        return set(tpl.provider for tpl in self.possible_templates)

    @property
    def appliances(self):
        return Appliance.objects.filter(appliance_pool=self).order_by("id").all()

    @property
    def current_count(self):
        return len(self.appliances)

    @property
    def percent_finished(self):
        if self.total_count is None:
            return 0.0
        total = 4 * self.total_count
        if total == 0:
            return 1.0
        finished = 0
        for appliance in self.appliances:
            if appliance.power_state not in {Appliance.Power.UNKNOWN, Appliance.Power.ORPHANED}:
                finished += 1
            if appliance.power_state == Appliance.Power.ON:
                finished += 1
            if appliance.ip_address is not None:
                finished += 1
            if appliance.ready:
                finished += 1
        return float(finished) / float(total)

    @property
    def appliance_ips(self):
        return [ap.ip_address for ap in filter(lambda a: a.ip_address is not None, self.appliances)]

    @property
    def fulfilled(self):
        try:
            return len(self.appliance_ips) == self.total_count\
                and all(a.ready for a in self.appliances)
        except ObjectDoesNotExist:
            return False

    @property
    def queued_provision_tasks(self):
        return DelayedProvisionTask.objects.filter(pool=self).order_by("id")

    def prolong_lease(self, time=60):
        self.logger.info("Initiated lease prolonging by {} minutes".format(time))
        for appliance in self.appliances:
            appliance.prolong_lease(time=time)

    def kill(self):
        with transaction.atomic():
            p = type(self).objects.get(pk=self.pk)
            p.not_needed_anymore = True
            p.save()
        save_lives = not self.finished
        self.logger.info("Killing")
        if self.appliances:
            for appliance in self.appliances:
                if (
                        save_lives and appliance.ready and appliance.leased_until is None
                        and appliance.marked_for_deletion is False
                        and not appliance.managed_providers):
                    with transaction.atomic():
                        with appliance.kill_lock:
                            appliance.appliance_pool = None
                            appliance.datetime_leased = None
                            appliance.save()
                        self.total_count -= 1
                        if self.total_count < 0:
                            self.total_count = 0  # Protection against stupidity
                        self.save()
                    appliance.set_status(
                        "The appliance was taken out of dying pool {}".format(self.id))
                else:
                    Appliance.kill(appliance)

            if self.current_count == 0:
                # Pool is empty, no point of keeping it alive.
                # This is needed when deleting a pool that has appliances that can be salvaged.
                # They are not deleted. the .delete() method on appliances takes care that when the
                # last appliance in pool is deleted, it deletes the pool. But since we don't delete
                # in the case of salvaging them, we do have to do it manually here.
                self.delete()
        else:
            # No appliances, so just delete it
            self.delete()

    @property
    def possible_other_owners(self):
        """Returns a list of User objects that can own this pool instead of original owner"""
        return type(self.owner).objects.exclude(pk=self.owner.pk).order_by("last_name",
                                                                           "first_name")

    @property
    def num_delayed_provisioning_tasks(self):
        return len(self.queued_provision_tasks)

    @property
    def num_provisioning_tasks_before(self):
        tasks = self.queued_provision_tasks
        if len(tasks) == 0:
            return 0
        latest_id = tasks[0].id
        return len(DelayedProvisionTask.objects.filter(id__lt=latest_id))

    @property
    def num_possible_provisioning_slots(self):
        providers = set([])
        for template in self.possible_provisioning_templates:
            providers.add(template.provider)
        slots = 0
        for provider in providers:
            slots += provider.remaining_provisioning_slots
        return slots

    @property
    def num_possible_appliance_slots(self):
        providers = set([])
        for template in self.possible_templates:
            providers.add(template.provider)
        slots = 0
        for provider in providers:
            slots += provider.remaining_appliance_slots
        return slots

    @property
    def num_shepherd_appliances(self):
        return len(Appliance.objects.filter(appliance_pool=None, **self.appliance_filter_params))

    def __repr__(self):
        return "<AppliancePool id: {}, group: {}, total_count: {}>".format(
            self.id, self.group.id, self.total_count)

    def __unicode__(self):
        return "AppliancePool id: {}, group: {}, total_count: {}".format(
            self.id, self.group.id, self.total_count)


class MismatchVersionMailer(models.Model):
    provider = models.ForeignKey(Provider)
    template_name = models.CharField(max_length=64)
    supposed_version = models.CharField(max_length=32)
    actual_version = models.CharField(max_length=32)
    sent = models.BooleanField(default=False)


class UserApplianceQuota(models.Model):
    user = models.OneToOneField(User, related_name="quotas")
    per_pool_quota = models.IntegerField(null=True, blank=True)
    total_pool_quota = models.IntegerField(null=True, blank=True)
    total_vm_quota = models.IntegerField(null=True, blank=True)
