# -*- coding: utf-8 -*-
from functools import wraps
from celery import chain
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models.query import QuerySet

from django_object_actions import DjangoObjectActions

# Register your models here.
from appliances.models import (
    Provider, Template, Appliance, Group, AppliancePool, DelayedProvisionTask,
    MismatchVersionMailer, UserApplianceQuota, User, BugQuery, GroupShepherd)
from appliances import tasks
from sprout.log import create_logger


def action(label, short_description):
    """Shortcut for actions"""
    def g(f):
        @wraps(f)
        def processed_action(self, request, objects):
            if not isinstance(objects, QuerySet):
                objects = [objects]
            return f(self, request, objects)
        processed_action.label = label
        processed_action.short_description = short_description
        return processed_action
    return g


def register_for(model, reregister=False):
    def f(modeladmin):
        if reregister:
            admin.site.unregister(model)
        admin.site.register(model, modeladmin)
        return modeladmin
    return f


class Admin(DjangoObjectActions, admin.ModelAdmin):
    @property
    def logger(self):
        return create_logger(self)


@register_for(DelayedProvisionTask)
class DelayedProvisionTaskAdmin(Admin):
    pass


@register_for(GroupShepherd)
class GroupShepherdAdmin(Admin):
    pass


@register_for(Appliance)
class ApplianceAdmin(Admin):
    objectactions = ["power_off", "power_on", "suspend", "kill"]
    actions = objectactions
    list_display = [
        "name", "owner", "template", "appliance_pool", "ready", "show_ip_address", "power_state"]
    readonly_fields = ["owner"]

    @action("Power off", "Power off selected appliance")
    def power_off(self, request, appliances):
        for appliance in appliances:
            tasks.appliance_power_off.delay(appliance.id)
            self.message_user(request, "Initiated poweroff of {}.".format(appliance.name))
            self.logger.info(
                "User {}/{} requested poweroff of appliance {}".format(
                    request.user.pk, request.user.username, appliance.id))

    @action("Power on", "Power on selected appliance")
    def power_on(self, request, appliances):
        for appliance in appliances:
            task_list = [tasks.appliance_power_on.si(appliance.id)]
            if appliance.preconfigured:
                task_list.append(tasks.wait_appliance_ready.si(appliance.id))
            else:
                task_list.append(tasks.mark_appliance_ready.si(appliance.id))
            chain(*task_list)()
            self.message_user(request, "Initiated poweron of {}.".format(appliance.name))
            self.logger.info(
                "User {}/{} requested poweron of appliance {}".format(
                    request.user.pk, request.user.username, appliance.id))

    @action("Suspend", "Suspend selected appliance")
    def suspend(self, request, appliances):
        for appliance in appliances:
            tasks.appliance_suspend.delay(appliance.id)
            self.message_user(request, "Initiated suspend of {}.".format(appliance.name))
            self.logger.info(
                "User {}/{} requested suspend of appliance {}".format(
                    request.user.pk, request.user.username, appliance.id))

    @action("Kill", "Kill selected appliance")
    def kill(self, request, appliances):
        for appliance in appliances:
            Appliance.kill(appliance)
            self.message_user(request, "Initiated kill of {}.".format(appliance.name))
            self.logger.info(
                "User {}/{} requested kill of appliance {}".format(
                    request.user.pk, request.user.username, appliance.id))

    def owner(self, instance):
        if instance.owner is not None:
            return instance.owner.username
        else:
            return "--- no owner ---"

    def show_ip_address(self, instance):
        if instance.ip_address:
            return "<a href=\"https://{ip}/\" target=\"_blank\">{ip}</a>".format(
                ip=instance.ip_address)
        else:
            return "---"
    show_ip_address.allow_tags = True
    show_ip_address.short_description = "IP address"


@register_for(AppliancePool)
class AppliancePoolAdmin(Admin):
    objectactions = ["kill"]
    actions = objectactions
    list_display = [
        "id", "group", "version", "date", "owner", "fulfilled", "appliances_ready",
        "queued_provision_tasks", "percent_finished", "total_count", "current_count"]
    readonly_fields = [
        "fulfilled", "appliances_ready", "queued_provision_tasks", "percent_finished",
        "current_count"]

    @action("Kill", "Kill the appliance pool")
    def kill(self, request, pools):
        for pool in pools:
            pool.kill()
            self.message_user(request, "Initiated kill of appliance pool {}".format(pool.id))
            self.logger.info(
                "User {}/{} requested kill of pool {}".format(
                    request.user.pk, request.user.username, pool.id))

    def fulfilled(self, instance):
        return instance.fulfilled
    fulfilled.boolean = True

    def appliances_ready(self, instance):
        return len(instance.appliance_ips)

    def queued_provision_tasks(self, instance):
        return len(instance.queued_provision_tasks)

    def percent_finished(self, instance):
        return "{0:.2f}%".format(round(instance.percent_finished * 100.0, 2))

    def current_count(self, instance):
        return instance.current_count


@register_for(Group)
class GroupAdmin(Admin):
    pass


@register_for(Provider)
class ProviderAdmin(Admin):
    readonly_fields = [
        "remaining_provisioning_slots", "provisioning_load", "show_ip_address", "appliance_load"]
    list_display = [
        "id", "working", "num_simultaneous_provisioning", "remaining_provisioning_slots",
        "provisioning_load", "show_ip_address", "appliance_load"]

    def remaining_provisioning_slots(self, instance):
        return str(instance.remaining_provisioning_slots)

    def appliance_load(self, instance):
        return "{0:.2f}%".format(round(instance.appliance_load * 100.0, 2))

    def provisioning_load(self, instance):
        return "{0:.2f}%".format(round(instance.provisioning_load * 100.0, 2))

    def show_ip_address(self, instance):
        if instance.ip_address:
            return "<a href=\"https://{ip}/\" target=\"_blank\">{ip}</a>".format(
                ip=instance.ip_address)
        else:
            return "---"
    show_ip_address.allow_tags = True
    show_ip_address.short_description = "IP address"


@register_for(Template)
class TemplateAdmin(Admin):
    list_display = [
        "name", "version", "original_name", "ready", "exists", "date", "template_group", "usable"]


@register_for(MismatchVersionMailer)
class MismatchVersionMailerAdmin(Admin):
    list_display = ["provider", "template_name", "supposed_version", "actual_version", "sent"]


class UserApplianceQuotaInline(admin.StackedInline):
    model = UserApplianceQuota
    can_delete = False


@register_for(User, reregister=True)
class CustomUserAdmin(UserAdmin):
    inlines = (UserApplianceQuotaInline, )


@register_for(BugQuery)
class BugQueryAdmin(Admin):
    pass
