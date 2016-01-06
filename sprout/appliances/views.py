# -*- coding: utf-8 -*-
import json

from celery import chain
from celery.result import AsyncResult
from dateutil import parser
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import transaction
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.shortcuts import render, redirect

from appliances.api import json_response
from appliances.models import (
    Provider, AppliancePool, Appliance, Group, Template, MismatchVersionMailer, User)
from appliances.tasks import (appliance_power_on, appliance_power_off, appliance_suspend,
    anyvm_power_on, anyvm_power_off, anyvm_suspend, anyvm_delete, delete_template_from_provider,
    appliance_rename, wait_appliance_ready, mark_appliance_ready, appliance_reboot)

from sprout.log import create_logger
from utils.providers import get_mgmt


def go_home(request):
    return redirect(index)


def go_back_or_home(request):
    ref = request.META.get('HTTP_REFERER')
    if ref:
        return redirect(ref)
    else:
        return go_home(request)


def index(request):
    superusers = User.objects.filter(is_superuser=True).order_by("last_name", "first_name")
    return render(request, 'index.html', locals())


def providers(request, provider_id=None):
    if provider_id is None:
        try:
            return redirect(
                "specific_provider", provider_id=Provider.objects.order_by("id")[0].id)
        except IndexError:
            # No Provider
            messages.info(request, "No provider present, redirected to the homepage.")
            return go_home(request)
    else:
        try:
            provider = Provider.objects.get(id=provider_id)
        except ObjectDoesNotExist:
            messages.warning(request, "Provider '{}' does not exist.".format(provider_id))
            return redirect("providers")
    providers = Provider.objects.order_by("id")
    complete_usage = Provider.complete_user_usage()
    return render(request, 'appliances/providers.html', locals())


def provider_usage(request):
    complete_usage = Provider.complete_user_usage()
    return render(request, 'appliances/provider_usage.html', locals())


def templates(request, group_id=None, prov_id=None):
    if group_id is None:
        try:
            return redirect("group_templates", group_id=Group.objects.order_by("id")[0].id)
        except IndexError:
            # No Group
            messages.info(request, "No group present, redirected to the homepage.")
            return go_home(request)
    else:
        try:
            group = Group.objects.get(id=group_id)
        except ObjectDoesNotExist:
            messages.warning(request, "Group '{}' does not exist.".format(group_id))
            return redirect("templates")
    if prov_id is not None:
        try:
            provider = Provider.objects.get(id=prov_id)
        except ObjectDoesNotExist:
            messages.warning(request, "Provider '{}' does not exist.".format(prov_id))
            return redirect("templates")
    else:
        provider = None
    groups = Group.objects.order_by("id")
    mismatched_versions = MismatchVersionMailer.objects.order_by("id")
    prepared_table = []
    zstream_rowspans = {}
    version_rowspans = {}
    for zstream, versions in group.zstreams_versions.iteritems():
        for version in versions:
            for provider in Provider.objects.all():
                for template in Template.objects.filter(
                        provider=provider, template_group=group, version=version, exists=True,
                        ready=True):
                    if zstream in zstream_rowspans:
                        zstream_rowspans[zstream] += 1
                        zstream_append = None
                    else:
                        zstream_rowspans[zstream] = 1
                        zstream_append = zstream

                    if version in version_rowspans:
                        version_rowspans[version] += 1
                        version_append = None
                    else:
                        version_rowspans[version] = 1
                        version_append = version
                    prepared_table.append((zstream_append, version_append, provider, template))
    return render(request, 'appliances/templates.html', locals())


def shepherd(request):
    if not request.user.is_authenticated():
        return go_home(request)
    groups = Group.objects.all()
    return render(request, 'appliances/shepherd.html', locals())


def versions_for_group(request):
    group_id = request.POST.get("stream")
    latest_version = None
    preconfigured = request.POST.get("preconfigured", "false").lower() == "true"
    if group_id == "<None>":
        versions = []
        group = None
    else:
        try:
            group = Group.objects.get(id=group_id)
        except ObjectDoesNotExist:
            versions = []
        else:
            versions = Template.get_versions(
                template_group=group, ready=True, usable=True, exists=True,
                preconfigured=preconfigured, provider__working=True, provider__disabled=False)
            if versions:
                latest_version = versions[0]

    return render(request, 'appliances/_versions.html', locals())


def date_for_group_and_version(request):
    group_id = request.POST.get("stream")
    latest_date = None
    preconfigured = request.POST.get("preconfigured", "false").lower() == "true"
    if group_id == "<None>":
        dates = []
    else:
        try:
            group = Group.objects.get(id=group_id)
        except ObjectDoesNotExist:
            dates = []
        else:
            version = request.POST.get("version")
            filters = {
                "template_group": group,
                "ready": True,
                "exists": True,
                "usable": True,
                "preconfigured": preconfigured,
                "provider__working": True,
            }
            if version == "latest":
                try:
                    versions = Template.get_versions(**filters)
                    filters["version"] = versions[0]
                except IndexError:
                    pass  # No such thing as version for this template group
            else:
                filters["version"] = version
            dates = Template.get_dates(**filters)
            if dates:
                latest_date = dates[0]
    return render(request, 'appliances/_dates.html', locals())


def providers_for_date_group_and_version(request):
    total_provisioning_slots = 0
    total_appliance_slots = 0
    total_shepherd_slots = 0
    shepherd_appliances = {}
    group_id = request.POST.get("stream")
    preconfigured = request.POST.get("preconfigured", "false").lower() == "true"
    if group_id == "<None>":
        providers = []
    else:
        try:
            group = Group.objects.get(id=group_id)
        except ObjectDoesNotExist:
            providers = []
        else:
            version = request.POST.get("version")
            filters = {
                "template_group": group,
                "ready": True,
                "exists": True,
                "usable": True,
                "preconfigured": preconfigured,
                "provider__working": True,
            }
            if version == "latest":
                try:
                    versions = Template.get_versions(**filters)
                    filters["version"] = versions[0]
                except IndexError:
                    pass  # No such thing as version for this template group
            else:
                filters["version"] = version
            date = request.POST.get("date")
            if date == "latest":
                try:
                    dates = Template.get_dates(**filters)
                    filters["date"] = dates[0]
                except IndexError:
                    pass  # No such thing as date for this template group
            else:
                filters["date"] = parser.parse(date)
            providers = Template.objects.filter(**filters).values("provider").distinct()
            providers = sorted([p.values()[0] for p in providers])
            providers = [Provider.objects.get(id=provider) for provider in providers]
            for provider in providers:
                appl_filter = dict(
                    appliance_pool=None, ready=True, template__provider=provider,
                    template__preconfigured=filters["preconfigured"],
                    template__template_group=filters["template_group"])
                if "date" in filters:
                    appl_filter["template__date"] = filters["date"]

                if "version" in filters:
                    appl_filter["template__version"] = filters["version"]
                shepherd_appliances[provider.id] = len(Appliance.objects.filter(**appl_filter))
                total_shepherd_slots += shepherd_appliances[provider.id]
                total_appliance_slots += provider.remaining_appliance_slots
                total_provisioning_slots += provider.remaining_provisioning_slots

            render_providers = {}
            for provider in providers:
                render_providers[provider.id] = {
                    "shepherd_count": shepherd_appliances[provider.id], "object": provider}
    return render(request, 'appliances/_providers.html', locals())


def my_appliances(request, show_user="my"):
    if not request.user.is_authenticated():
        return go_home(request)
    if not request.user.is_superuser:
        if not (show_user == "my" or show_user == request.user.username):
            messages.info(request, "You can't view others' appliances!")
            show_user = "my"
        if show_user == request.user.username:
            show_user = "my"
    else:
        other_users = User.objects.exclude(pk=request.user.pk).order_by("last_name", "first_name")
    if show_user == "my":
        pools = AppliancePool.objects.filter(owner=request.user).order_by("id")
    elif show_user == "all":
        pools = AppliancePool.objects.order_by("id")
    else:
        pools = AppliancePool.objects.filter(owner__username=show_user).order_by("id")
    groups = Group.objects.order_by("id")
    can_order_pool = show_user == "my"
    new_pool_possible = True
    display_legend = False
    for pool in pools:
        if not pool.finished:
            display_legend = True
    per_pool_quota = None
    pools_remaining = None
    num_user_vms = Appliance.objects.filter(appliance_pool__owner=request.user).count()
    if request.user.has_quotas:
        if request.user.quotas.total_pool_quota is not None:
            if request.user.quotas.total_pool_quota <= len(pools):
                new_pool_possible = False
            pools_remaining = request.user.quotas.total_pool_quota - len(pools)
        if request.user.quotas.total_vm_quota is not None:
            if request.user.quotas.total_vm_quota <= num_user_vms:
                new_pool_possible = False
        if request.user.quotas.per_pool_quota is not None:
            per_pool_quota = request.user.quotas.per_pool_quota
            remaining_vms = request.user.quotas.total_vm_quota - num_user_vms
            if remaining_vms < per_pool_quota:
                per_pool_quota = remaining_vms
    per_pool_quota_enabled = per_pool_quota is not None
    return render(request, 'appliances/my_appliances.html', locals())


def can_operate_appliance_or_pool(appliance_or_pool, user):
    if user.is_superuser:
        return True
    else:
        return appliance_or_pool.owner == user


def appliance_action(request, appliance_id, action, x=None):
    if not request.user.is_authenticated():
        return go_home(request)
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        messages.warning(request, 'Appliance with ID {} does not exist!.'.format(appliance_id))
        return go_back_or_home(request)
    if not can_operate_appliance_or_pool(appliance, request.user):
        messages.warning(request, 'This appliance belongs either to some other user or nobody.')
        return go_back_or_home(request)
    if action == "start":
        if appliance.power_state != Appliance.Power.ON:
            chain(
                appliance_power_on.si(appliance.id),
                (wait_appliance_ready if appliance.preconfigured else mark_appliance_ready).si(
                    appliance.id))()
            messages.success(request, 'Initiated launch of appliance.')
            return go_back_or_home(request)
        else:
            messages.info(request, 'Appliance was already powered on.')
            return go_back_or_home(request)
    elif action == "reboot":
        if appliance.power_state == Appliance.Power.ON:
            chain(
                appliance_reboot.si(appliance.id),
                (wait_appliance_ready if appliance.preconfigured else mark_appliance_ready).si(
                    appliance.id))()
            messages.success(request, 'Initiated reboot of appliance.')
            return go_back_or_home(request)
        else:
            messages.warning(request, 'Only powered on appliances can be rebooted')
            return go_back_or_home(request)
    elif action == "stop":
        if appliance.power_state != Appliance.Power.OFF:
            appliance_power_off.delay(appliance.id)
            messages.success(request, 'Initiated stop of appliance.')
            return go_back_or_home(request)
        else:
            messages.info(request, 'Appliance was already powered off.')
            return go_back_or_home(request)
    elif action == "suspend":
        if appliance.power_state != Appliance.Power.SUSPENDED:
            appliance_suspend.delay(appliance.id)
            messages.success(request, 'Initiated suspend of appliance.')
            return go_back_or_home(request)
        else:
            messages.info(request, 'Appliance was already suspended.')
            return go_back_or_home(request)
    elif action == "kill":
        Appliance.kill(appliance)
        messages.success(request, 'Kill initiated.')
        return go_back_or_home(request)
    elif action == "dont_expire":
        if not request.user.is_superuser:
            messages.warning(request, 'Disabling expiration time is allowed only for superusers.')
            return go_back_or_home(request)
        with transaction.atomic():
            appliance.leased_until = None
            appliance.save()
        messages.success(request, 'Lease disabled successfully. Be careful.')
        return go_back_or_home(request)
    elif action == "set_lease":
        if not can_operate_appliance_or_pool(appliance, request.user):
            messages.warning(request, 'This appliance belongs either to some other user or nobody.')
            return go_back_or_home(request)
        appliance.prolong_lease(time=int(x))
        messages.success(request, 'Lease prolonged successfully.')
        return go_back_or_home(request)
    else:
        messages.warning(request, "Unknown action '{}'".format(action))


def prolong_lease_pool(request, pool_id, minutes):
    if not request.user.is_authenticated():
        return go_home(request)
    try:
        appliance_pool = AppliancePool.objects.get(id=pool_id)
    except ObjectDoesNotExist:
        messages.warning(request, 'Appliance pool with ID {} does not exist!.'.format(pool_id))
        return go_back_or_home(request)
    if not can_operate_appliance_or_pool(appliance_pool, request.user):
        messages.warning(request, 'This appliance belongs either to some other user or nobody.')
        return go_back_or_home(request)
    appliance_pool.prolong_lease(time=int(minutes))
    messages.success(request, 'Lease prolonged successfully.')
    return go_back_or_home(request)


def dont_expire_pool(request, pool_id):
    if not request.user.is_authenticated():
        return go_home(request)
    try:
        appliance_pool = AppliancePool.objects.get(id=pool_id)
    except ObjectDoesNotExist:
        messages.warning(request, 'Pool with ID {} does not exist!.'.format(pool_id))
        return go_back_or_home(request)
    if not request.user.is_superuser:
        messages.warning(request, 'Disabling expiration time is allowed only for superusers.')
        return go_back_or_home(request)
    with transaction.atomic():
        for appliance in appliance_pool.appliances:
            appliance.leased_until = None
            appliance.save()
    messages.success(request, 'Lease disabled successfully. Be careful.')
    return go_back_or_home(request)


def kill_pool(request, pool_id):
    if not request.user.is_authenticated():
        return go_home(request)
    try:
        pool = AppliancePool.objects.get(id=pool_id)
    except ObjectDoesNotExist:
        messages.warning(request, 'Pool with ID {} does not exist!.'.format(pool_id))
        return go_back_or_home(request)
    if not can_operate_appliance_or_pool(pool, request.user):
        messages.warning(request, 'This pool belongs either to some other user or nobody.')
        return go_back_or_home(request)
    try:
        pool.kill()
    except Exception as e:
        messages.warning(request, "Exception {}: {}".format(type(e).__name__, str(e)))
    else:
        messages.success(request, 'Kill successfully initiated.')
    return go_back_or_home(request)


def set_pool_description(request):
    if not request.user.is_authenticated():
        raise PermissionDenied()
    try:
        pool_id = request.POST.get("pool_id", None)
        pool = AppliancePool.objects.get(id=pool_id)
    except ObjectDoesNotExist:
        raise Http404('Pool with ID {} does not exist!.'.format(pool_id))
    if not can_operate_appliance_or_pool(pool, request.user):
        raise PermissionDenied()
    description = request.POST.get("description", None)
    pool.description = description
    pool.save()
    return HttpResponse("")


def delete_template_provider(request):
    if not request.user.is_authenticated():
        return HttpResponseForbidden("Only authenticated superusers can operate this action.")
    template_id = request.POST["template_id"]
    try:
        template = Template.objects.get(id=template_id)
    except ObjectDoesNotExist:
        raise Http404('Template with ID {} does not exist!.'.format(template_id))
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only superusers can operate this action.")
    task = delete_template_from_provider.delay(template.id)
    return HttpResponse(task.id)


def request_pool(request):
    if not request.user.is_authenticated():
        return go_home(request)
    try:
        group = request.POST["stream"]
        version = request.POST["version"]
        if version == "latest":
            version = None
        date = request.POST["date"]
        if date == "latest":
            date = None
        provider = request.POST["provider"]
        if provider == "any":
            provider = None
        preconfigured = request.POST.get("preconfigured", "false").lower() == "true"
        yum_update = request.POST.get("yum_update", "false").lower() == "true"
        count = int(request.POST["count"])
        lease_time = int(request.POST.get("expiration", 60))
        pool_id = AppliancePool.create(
            request.user, group, version, date, provider, count, lease_time, preconfigured,
            yum_update).id
        messages.success(request, "Pool requested - id {}".format(pool_id))
    except Exception as e:
        messages.warning(request, "Exception {} happened: {}".format(type(e).__name__, str(e)))
    return go_back_or_home(request)


def transfer_pool(request):
    if not request.user.is_authenticated():
        return go_home(request)
    try:
        pool_id = int(request.POST["pool_id"])
        user_id = int(request.POST["user_id"])
        with transaction.atomic():
            pool = AppliancePool.objects.get(id=pool_id)
            if not request.user.is_superuser:
                if pool.owner != request.user:
                    raise Exception("User does not have the right to change this pool's owner!")
            user = User.objects.get(id=user_id)
            if user == request.user:
                raise Exception("Why changing owner back to yourself? That does not make sense!")
            # original_owner = pool.owner
            pool.owner = user
            pool.save()
        # Rename appliances
        # for appliance in pool.appliances:
        #     if appliance.name.startswith("{}_".format(original_owner.username)):
        #         # Change name
        #         appliance_rename.delay(
        #             appliance.id, user.username + appliance.name[len(original_owner.username):])
    except Exception as e:
        messages.warning(request, "Exception {} happened: {}".format(type(e).__name__, str(e)))
    else:
        messages.success(request, "Success!")
    finally:
        return go_back_or_home(request)


def vms(request, current_provider=None):
    if not request.user.is_authenticated():
        return go_home(request)
    provider_keys = sorted(Provider.get_available_provider_keys())
    providers = []
    for provider_key in provider_keys:
        try:
            provider = Provider.objects.get(id=provider_key)
        except ObjectDoesNotExist:
            providers.append((provider_key, True))
        else:
            providers.append((provider_key, provider.is_working))
    if current_provider is None and providers:
        return redirect("vms_at_provider", current_provider=provider_keys[0])
    return render(request, 'appliances/vms/index.html', locals())


def vms_table(request, current_provider=None):
    if not request.user.is_authenticated():
        return go_home(request)
    manager = get_mgmt(current_provider)
    vms = sorted(manager.list_vm())
    return render(request, 'appliances/vms/_list.html', locals())


def power_state(request, current_provider):
    vm_name = request.POST["vm_name"]
    manager = get_mgmt(current_provider)
    state = Appliance.POWER_STATES_MAPPING.get(manager.vm_status(vm_name), "unknown")
    return HttpResponse(state, content_type="text/plain")


def power_state_buttons(request, current_provider):
    manager = get_mgmt(current_provider)
    vm_name = request.POST["vm_name"]
    power_state = request.POST["power_state"]
    can_power_on = power_state in {Appliance.Power.SUSPENDED, Appliance.Power.OFF}
    can_power_off = power_state in {Appliance.Power.ON}
    can_suspend = power_state in {Appliance.Power.ON} and manager.can_suspend
    can_delete = power_state in {Appliance.Power.OFF}
    return render(request, 'appliances/vms/_buttons.html', locals())


def vm_action(request, current_provider):
    if not request.user.is_authenticated():
        return HttpResponse("Not authenticated", content_type="text/plain")
    try:
        get_mgmt(current_provider)
    except Exception as e:
        return HttpResponse(
            "Troubles with provider {}: {}".format(current_provider, str(e)),
            content_type="text/plain")
    vm_name = request.POST["vm_name"]
    action = request.POST["action"]
    if action == "poweron":
        anyvm_power_on.delay(current_provider, vm_name)
    elif action == "poweroff":
        anyvm_power_off.delay(current_provider, vm_name)
    elif action == "suspend":
        anyvm_suspend.delay(current_provider, vm_name)
    elif action == "delete":
        anyvm_delete.delay(current_provider, vm_name)
    else:
        HttpResponse("No such action {}!".format(action), content_type="text/plain")
    logger().info("User {} initiated {} on {}@{}".format(
        request.user.username, action, vm_name, current_provider))
    return HttpResponse("Action {} was initiated".format(action), content_type="text/plain")


def logger():
    return create_logger("sprout_vm_actions")


def rename_appliance(request):
    post = json.loads(request.body)
    if not request.user.is_authenticated():
        raise PermissionDenied()
    try:
        appliance_id = post.get("appliance_id")
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        raise Http404('Appliance with ID {} does not exist!.'.format(appliance_id))
    if not can_operate_appliance_or_pool(appliance, request.user):
        raise PermissionDenied("Permission denied")
    new_name = post.get("new_name")
    return HttpResponse(str(appliance_rename.delay(appliance.id, new_name).task_id))


def task_result(request):
    post = json.loads(request.body)
    task_id = post.get("task_id")
    result = AsyncResult(task_id)
    if not result.ready():
        return json_response(None)
    return json_response(result.get(timeout=1))


def provider_enable_disable(request, provider_id, disabled=None):
    if not request.user.is_authenticated():
        return go_home(request)
    try:
        provider = Provider.objects.get(id=provider_id)
    except ObjectDoesNotExist:
        messages.warning(request, 'Provider with ID {} does not exist!.'.format(provider_id))
        return go_back_or_home(request)
    if not request.user.is_superuser:
        messages.warning(request, 'Providers can be modified only by superusers.')
        return go_back_or_home(request)
    provider.disabled = disabled
    provider.save()
    messages.success(
        request, 'Provider {}, {}.'.format(provider_id, "disabled" if disabled else "enabled"))
    return go_back_or_home(request)
