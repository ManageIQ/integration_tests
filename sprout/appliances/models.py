# -*- coding: utf-8 -*-
from datetime import timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.utils import timezone

from utils.appliance import Appliance as CFMEAppliance
from utils.conf import cfme_data
from utils.log import create_logger
from utils.providers import provider_factory
from utils.version import LooseVersion


def logger():
    return create_logger("sprout")


class Provider(models.Model):
    id = models.CharField(max_length=32, primary_key=True, help_text="Provider's key in YAML.")
    working = models.BooleanField(default=False, help_text="Whether provider is available.")
    num_simultaneous_provisioning = models.IntegerField(default=5,
        help_text="How many simultaneous background provisioning tasks can run on this provider.")

    @property
    def api(self):
        return provider_factory(self.id)

    @property
    def num_currently_provisioning(self):
        return len(
            Appliance.objects.filter(
                ready=False, marked_for_deletion=False, template__provider=self))

    @property
    def remaining_provisioning_slots(self):
        result = self.num_simultaneous_provisioning - self.num_currently_provisioning
        if result < 0:
            return 0
        else:
            return result

    @property
    def free(self):
        return self.remaining_provisioning_slots > 0

    @classmethod
    def get_available_provider_keys(cls):
        return cfme_data.get("management_systems", {}).keys()

    @property
    def provider_data(self):
        return cfme_data.get("management_systems", {}).get(self.id, {})

    def __unicode__(self):
        return "{} {}".format(self.__class__.__name__, self.id)


class Group(models.Model):
    id = models.CharField(max_length=32, primary_key=True,
        help_text="Group name as trackerbot says. (eg. upstream, downstream-53z, ...)")
    template_pool_size = models.IntegerField(default=0,
        help_text="How many appliances to keep spinned for quick taking.")

    def __unicode__(self):
        return "{} {} (pool size={})".format(
            self.__class__.__name__, self.id, self.template_pool_size)


class Template(models.Model):
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
    def is_created(self):
        return self.provider_api.does_vm_exist(self.name)

    @property
    def cfme(self):
        return CFMEAppliance(self.provider_name, self.name)

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


class Appliance(models.Model):
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

    marked_for_deletion = models.BooleanField(default=False,
        help_text="Appliance is already being deleted.")

    power_state = models.CharField(max_length=32, default="unknown",
        help_text="Appliance's power state")
    ready = models.BooleanField(default=False,
        help_text="Appliance has an IP address and web UI is online.")

    @property
    def provider_api(self):
        return self.template.provider_api

    @property
    def provider_name(self):
        return self.template.provider_name

    @property
    def cfme(self):
        return CFMEAppliance(self.provider_name, self.name)

    def retrieve_power_state(self):
        api = self.provider_api
        exists = api.does_vm_exist(self.name)
        if not exists:
            with transaction.atomic():
                appliance = Appliance.objects.get(id=self.id)
                appliance.power_state = self.Power.ORPHANED
                appliance.save()
                return
        # Appliance present
        power_state = api.vm_status(self.name)
        with transaction.atomic():
            appliance = Appliance.objects.get(id=self.id)
            if power_state in appliance.POWER_STATES_MAPPING:
                appliance.power_state = appliance.POWER_STATES_MAPPING[power_state]
            else:
                appliance.power_state = appliance.Power.UNKNOWN
            appliance.save()

    def set_status(self, status):
        with transaction.atomic():
            appliance = Appliance.objects.get(id=self.id)
            appliance.status = status
            appliance.status_changed = timezone.now()
            appliance.save()
            logger().info("{}: {}".format(str(self), status))

    def __unicode__(self):
        return "{} {} @ {}".format(self.__class__.__name__, self.name, self.template.provider.id)

    @classmethod
    def unassigned(cls):
        return cls.objects.filter(appliance_pool=None, ready=True)

    @classmethod
    def give_to_pool(cls, pool, time_minutes):
        from appliances.tasks import appliance_power_on
        n_appliances = 0
        with transaction.atomic():
            for template in pool.possible_templates:
                for appliance in cls.unassigned().filter(
                        template=template).all()[:pool.total_count - n_appliances]:
                    appliance.appliance_pool = pool
                    appliance.datetime_leased = timezone.now()
                    appliance.leased_until = appliance.datetime_leased + timedelta(
                        minutes=time_minutes)
                    if appliance.provider_api.can_rename:
                        new_name = "{}_{}".format(pool.owner.username, appliance.name)
                        try:
                            appliance.provider_api.rename_vm(appliance.name, new_name)
                        except Exception as e:
                            logger().exception(str(e))
                        else:
                            appliance.name = new_name
                    appliance.save()
                    appliance_power_on.delay(appliance.id)
                    n_appliances += 1
                if n_appliances == pool.total_count:
                    break
        return n_appliances

    @classmethod
    def kill(cls, appliance_or_id):
        # Completely delete appliance from provider
        from appliances.tasks import kill_appliance
        with transaction.atomic():
            if isinstance(appliance_or_id, cls):
                self = Appliance.objects.get(id=appliance_or_id.id)
            else:
                self = Appliance.objects.get(id=appliance_or_id)
            if not self.marked_for_deletion:
                self.marked_for_deletion = True
                self.leased_until = None
                self.save()
                return kill_appliance.delay(self.id)

    def delete(self, *args, **kwargs):
        # Intercept delete and lessen the number of appliances in the pool
        # Then if the appliance is still present in the management system, kill it
        with transaction.atomic():
            if self.appliance_pool is not None:
                self.appliance_pool.total_count -= 1
                if self.appliance_pool.total_count > 0:
                    self.appliance_pool.save()
                else:
                    pool = self.appliance_pool
                    self.appliance_pool = None
                    self.save()
                    pool.delete()

        # if self.provider_api.does_vm_exist(self.name):
        #     from appliances.tasks import kill_appliance
        #     kill_appliance.delay(self.id)
        return super(Appliance, self).delete(*args, **kwargs)

    def prolong_lease(self, time=60):
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


class AppliancePool(models.Model):
    total_count = models.IntegerField(help_text="How many appliances should be in this pool.")
    group = models.ForeignKey(Group, help_text="Group which is used to provision appliances.")
    version = models.CharField(max_length=16, null=True, help_text="Appliance version")
    date = models.DateField(null=True, help_text="Appliance date.")
    owner = models.ForeignKey(User, help_text="User who owns the appliance pool")

    @classmethod
    def create(cls, owner, group, version=None, date=None, num_appliances=1, time_leased=60):
        from appliances.tasks import request_appliance_pool
        # Retrieve latest possible
        if not version:
            versions = Template.get_versions(template_group=group)
            if versions:
                version = versions[0]
        if not date:
            dates = Template.get_dates(template_group=group)
            if dates:
                date = dates[0]
        if isinstance(group, basestring):
            group = Group.objects.get(id=group)
        if not (version or date):
            raise Exception("Could not find possible combination of group, date and version!")
        req = cls(group=group, version=version, date=date, total_count=num_appliances, owner=owner)
        if not req.possible_templates:
            raise Exception("No possible templates!")
        req.save()
        request_appliance_pool.delay(req.id, time_leased)
        return req

    @property
    def possible_templates(self):
        filter_params = {}
        if self.version is not None:
            filter_params["version"] = self.version
        if self.date is not None:
            filter_params["date"] = self.date
        return Template.objects.filter(
            template_group=self.group, ready=True, exists=True, **filter_params).all()

    @property
    def appliances(self):
        return Appliance.objects.filter(appliance_pool=self).all()

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

    def prolong_lease(self, time=60):
        for appliance in self.appliances:
            appliance.prolong_lease(time=time)

    def kill(self):
        for appliance in self.appliances:
            Appliance.kill(appliance)

    def __repr__(self):
        return "<AppliancePool id: {}, group: {}, total_count: {}>".format(
            self.id, self.group.id, self.total_count)

    def __unicode__(self):
        return "AppliancePool id: {}, group: {}, total_count: {}".format(
            self.id, self.group.id, self.total_count)
