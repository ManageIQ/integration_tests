# -*- coding: utf-8 -*-
import yaml

from contextlib import contextmanager
from datetime import timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.utils import timezone

from sprout import critical_section

from utils import mgmt_system
from utils.appliance import Appliance as CFMEAppliance, IPAppliance
from utils.conf import cfme_data
from utils.log import create_logger
from utils.providers import provider_factory
from utils.timeutil import nice_seconds
from utils.version import LooseVersion


def logger():
    return create_logger("sprout")


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
        with critical_section("({})[{}]".format(self.__class__.__name__, str(self.pk))):
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
        return provider_factory(self.id)

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
        logger().info("Running cleanup on provider {}".format(self.id))
        if isinstance(self.api, mgmt_system.OpenstackSystem):
            # Openstack cleanup
            # Clean up the floating IPs
            for floating_ip in self.api.api.floating_ips.findall(fixed_ip=None):
                logger().info("Cleaning up the {} floating ip {}".format(self.id, floating_ip.ip))
                try:
                    floating_ip.delete()
                except Exception as e:
                    logger().exception(e)

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

    @property
    def templates(self):
        return Template.objects.filter(template_group=self).order_by("-date", "provider__id")

    @property
    def existing_templates(self):
        return self.templates.filter(exists=True)

    @property
    def appliances(self):
        return Appliance.objects.filter(template__template_group=self)

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
            logger().info("{}: {}".format(str(self), status))

    @property
    def cfme(self):
        return CFMEAppliance(self.provider_name, self.name)

    @property
    def can_be_deleted(self):
        return self.exists and self.preconfigured

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
        versions.sort(key=LooseVersion, reverse=True)
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
        )

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
            appliance.status = status
            appliance.status_changed = timezone.now()
            appliance.save()
            logger().info("{}: {}".format(str(self), status))

    def set_power_state(self, power_state):
        if power_state != self.power_state:
            logger().info("{} changed power state to {}".format(self.name, power_state))
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
        from appliances.tasks import appliance_power_on
        limit = custom_limit if custom_limit is not None else pool.total_count
        appliances = []
        with transaction.atomic():
            for template in pool.possible_templates:
                for appliance in cls.unassigned().filter(
                        template=template).all()[:limit - len(appliances)]:
                    appliance.appliance_pool = pool
                    appliance.save()
                    appliance.set_status("Given to pool {}".format(pool.id))
                    appliance_power_on.delay(appliance.id)
                    appliances.append(appliance)
                if len(appliances) == limit:
                    break
        return len(appliances)

    @classmethod
    def kill(cls, appliance_or_id):
        # Completely delete appliance from provider
        from appliances.tasks import kill_appliance
        with transaction.atomic():
            if isinstance(appliance_or_id, cls):
                self = Appliance.objects.get(id=appliance_or_id.id)
            else:
                self = Appliance.objects.get(id=appliance_or_id)
            logger().info("Killing appliance {}".format(self.id))
            if not self.marked_for_deletion:
                self.marked_for_deletion = True
                self.leased_until = None
                self.save()
                return kill_appliance.delay(self.id)

    def delete(self, *args, **kwargs):
        # Intercept delete and lessen the number of appliances in the pool
        # Then if the appliance is still present in the management system, kill it
        logger().info("Deleting appliance {}".format(self.id))
        pool = self.appliance_pool
        result = super(Appliance, self).delete(*args, **kwargs)
        do_not_touch = kwargs.pop("do_not_touch_ap", False)
        if pool is not None and not do_not_touch:
            if pool.current_count == 0:
                pool.delete()
        return result

    def prolong_lease(self, time=60):
        logger().info("Prolonging lease of {} by {} minutes.".format(self.id, time))
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
        return self.provider.vnc_console_link_for(self)


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

    @classmethod
    def create(cls, owner, group, version=None, date=None, provider=None, num_appliances=1,
            time_leased=60, preconfigured=True):
        from appliances.tasks import request_appliance_pool
        # Retrieve latest possible
        if not version:
            versions = Template.get_versions(
                template_group=group, ready=True, usable=True, preconfigured=preconfigured)
            if versions:
                version = versions[0]
        if not date:
            if version is not None:
                dates = Template.get_dates(template_group=group, version=version, ready=True,
                    usable=True, preconfigured=preconfigured)
            else:
                dates = Template.get_dates(
                    template_group=group, ready=True, usable=True, preconfigured=preconfigured)
            if dates:
                date = dates[0]
        if isinstance(group, basestring):
            group = Group.objects.get(id=group)
        if isinstance(provider, basestring):
            provider = Provider.objects.get(id=provider)
        if not (version or date):
            raise Exception("Could not find possible combination of group, date and version!")
        req = cls(
            group=group, version=version, date=date, total_count=num_appliances, owner=owner,
            provider=provider, preconfigured=preconfigured)
        if not req.possible_templates:
            raise Exception("No possible templates! (query: {}".format(str(req.__dict__)))
        req.save()
        logger().info("Appliance pool {} created".format(req.id))
        request_appliance_pool.delay(req.id, time_leased)
        return req

    def delete(self, *args, **kwargs):
        logger().info("Deleting appliance pool {}".format(self.id))
        with transaction.atomic():
            for task in DelayedProvisionTask.objects.filter(pool=self):
                task.delete()

        return super(AppliancePool, self).delete(*args, **kwargs)

    @property
    def possible_templates(self):
        filter_params = {}
        if self.version is not None:
            filter_params["version"] = self.version
        if self.date is not None:
            filter_params["date"] = self.date
        if self.provider is not None:
            filter_params["provider"] = self.provider
        return Template.objects.filter(
            template_group=self.group, ready=True, exists=True, usable=True,
            preconfigured=self.preconfigured, **filter_params).all()

    @property
    def possible_provisioning_templates(self):
        return sorted(
            filter(lambda tpl: tpl.provider.free, self.possible_templates),
            # Sort by date and load to pick the best match (least loaded provider)
            key=lambda tpl: (tpl.date, 1.0 - tpl.provider.appliance_load), reverse=True)

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
        """Like partially_fulfilled, but also count of applinces must match the total_count."""
        try:
            return len(self.appliance_ips) == self.total_count\
                and all(a.ready for a in self.appliances)
        except ObjectDoesNotExist:
            return False

    @property
    def partially_fulfilled(self):
        """All appliances that are in the pool are ready."""
        try:
            return all(a.ready for a in self.appliances)
        except ObjectDoesNotExist:
            return False

    @property
    def queued_provision_tasks(self):
        return DelayedProvisionTask.objects.filter(pool=self)

    def drop_remaining_provisioning_tasks(self):
        with transaction.atomic():
            for task in self.queued_provision_tasks:
                task.delete()

    def prolong_lease(self, time=60):
        for appliance in self.appliances:
            appliance.prolong_lease(time=time)

    def kill(self):
        with transaction.atomic():
            p = type(self).objects.get(pk=self.pk)
            p.not_needed_anymore = True
            p.save()
        save_lives = not self.fulfilled
        if self.appliances:
            for appliance in self.appliances:
                # The leased_until is reliable sign of whether the appliance was used
                # Unless someone was messing with DB ;)
                if save_lives and appliance.ready and appliance.leased_until is None:
                    with transaction.atomic():
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
        else:
            # No appliances, so just delete it
            self.delete()

    @property
    def possible_other_owners(self):
        """Returns a list of User objects that can own this pool instead of original owner"""
        return type(self.owner).objects.exclude(pk=self.owner.pk).order_by("last_name",
                                                                           "first_name")

    def __repr__(self):
        return "<AppliancePool id: {}, group: {}, total_count: {}>".format(
            self.id, self.group.id, self.total_count)

    def __unicode__(self):
        return "AppliancePool id: {}, group: {}, total_count: {}".format(
            self.id, self.group.id, self.total_count)
