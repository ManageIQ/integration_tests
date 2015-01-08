# -*- coding: utf-8 -*-
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.base import add_to_builtins

from appliances.models import Provider, AppliancePool, Appliance, Group, Template
from appliances.tasks import (appliance_power_on, appliance_power_off, appliance_suspend,
    anyvm_power_on, anyvm_power_off, anyvm_suspend, anyvm_delete)

from utils.log import create_logger
from utils.providers import provider_factory

add_to_builtins('appliances.templatetags.appliances_extras')


def go_home(request):
    return redirect(index)


def go_back_or_home(request):
    ref = request.META.get('HTTP_REFERER')
    if ref:
        return redirect(ref)
    else:
        return go_home(request)


def index(request):
    superusers = User.objects.filter(is_superuser=True)
    return render(request, 'index.html', locals())


def providers(request):
    providers = Provider.objects.all()
    return render(request, 'appliances/providers.html', locals())


def shepherd(request):
    appliances = Appliance.objects.filter(
        appliance_pool=None, ready=True, marked_for_deletion=False)
    return render(request, 'appliances/shepherd.html', locals())


def versions_for_group(request):
    group_id = request.POST.get("stream")
    if group_id == "<None>":
        versions = []
        group = None
    else:
        try:
            group = Group.objects.get(id=group_id)
        except ObjectDoesNotExist:
            versions = []
        else:
            versions_only = Template.get_versions(template_group=group, ready=True, usable=True)
            versions = []
            for version in versions_only:
                providers = []
                for provider in Template.objects.filter(
                        version=version, usable=True, ready=True).values("provider"):
                    providers.append(provider.values()[0])
                versions.append((version, ", ".join(providers)))

    return render(request, 'appliances/_versions.html', locals())


def date_for_group_and_version(request):
    group_id = request.POST.get("stream")
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
                "exists": True
            }
            if version != "latest":
                filters["version"] = version
            dates = Template.get_dates(**filters)
    return render(request, 'appliances/_dates.html', locals())


def my_appliances(request):
    if not request.user.is_authenticated():
        return go_home(request)
    pools = AppliancePool.objects.filter(owner=request.user)
    groups = Group.objects.all()
    return render(request, 'appliances/my_appliances.html', locals())


def start_appliance(request, appliance_id):
    if not request.user.is_authenticated():
        return go_home(request)
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        messages.error(request, 'Appliance with ID {} does not exist!.'.format(appliance_id))
        return go_back_or_home(request)
    if appliance.owner is None or appliance.owner != request.user:
        messages.error(request, 'This appliance belongs either to some other user or nobody.')
        return go_back_or_home(request)
    if appliance.power_state != Appliance.Power.ON:
        appliance_power_on.delay(appliance.id)
        messages.success(request, 'Initiated launch of appliance.')
        return go_back_or_home(request)
    else:
        messages.info(request, 'Appliance was already powered on.')
        return go_back_or_home(request)


def stop_appliance(request, appliance_id):
    if not request.user.is_authenticated():
        return go_home(request)
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        messages.error(request, 'Appliance with ID {} does not exist!.'.format(appliance_id))
        return go_back_or_home(request)
    if appliance.owner is None or appliance.owner != request.user:
        messages.error(request, 'This appliance belongs either to some other user or nobody.')
        return go_back_or_home(request)
    if appliance.power_state != Appliance.Power.OFF:
        appliance_power_off.delay(appliance.id)
        messages.success(request, 'Initiated stop of appliance.')
        return go_back_or_home(request)
    else:
        messages.info(request, 'Appliance was already powered off.')
        return go_back_or_home(request)


def suspend_appliance(request, appliance_id):
    if not request.user.is_authenticated():
        return go_home(request)
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        messages.error(request, 'Appliance with ID {} does not exist!.'.format(appliance_id))
        return go_back_or_home(request)
    if appliance.owner is None or appliance.owner != request.user:
        messages.error(request, 'This appliance belongs either to some other user or nobody.')
        return go_back_or_home(request)
    if appliance.power_state != Appliance.Power.SUSPENDED:
        appliance_suspend.delay(appliance.id)
        messages.success(request, 'Initiated suspend of appliance.')
        return go_back_or_home(request)
    else:
        messages.info(request, 'Appliance was already suspended.')
        return go_back_or_home(request)


def prolong_lease_appliance(request, appliance_id, minutes):
    if not request.user.is_authenticated():
        return go_home(request)
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        messages.error(request, 'Appliance with ID {} does not exist!.'.format(appliance_id))
        return go_back_or_home(request)
    if appliance.owner is None or appliance.owner != request.user:
        messages.error(request, 'This appliance belongs either to some other user or nobody.')
        return go_back_or_home(request)
    appliance.prolong_lease(time=int(minutes))
    messages.success(request, 'Lease prolonged successfully.')
    return go_back_or_home(request)


def kill_appliance(request, appliance_id):
    if not request.user.is_authenticated():
        return go_home(request)
    try:
        appliance = Appliance.objects.get(id=appliance_id)
    except ObjectDoesNotExist:
        messages.error(request, 'Appliance with ID {} does not exist!.'.format(appliance_id))
        return go_back_or_home(request)
    if appliance.owner is None or appliance.owner != request.user:
        messages.error(request, 'This appliance belongs either to some other user or nobody.')
        return go_back_or_home(request)
    Appliance.kill(appliance)
    messages.success(request, 'Kill initiated.')
    return go_back_or_home(request)


def kill_pool(request, pool_id):
    if not request.user.is_authenticated():
        return go_home(request)
    try:
        pool = AppliancePool.objects.get(id=pool_id)
    except ObjectDoesNotExist:
        messages.error(request, 'Pool with ID {} does not exist!.'.format(pool_id))
        return go_back_or_home(request)
    if pool.owner is None or pool.owner != request.user:
        messages.error(request, 'This pool belongs either to some other user or nobody.')
        return go_back_or_home(request)
    try:
        pool.kill()
    except Exception as e:
        messages.error(request, "Exception {}: {}".format(type(e).__name__, str(e)))
    else:
        messages.success(request, 'Kill successfully initiated.')
    return go_back_or_home(request)


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
        count = int(request.POST["count"])
        lease_time = 60
        pool_id = AppliancePool.create(request.user, group, version, date, count, lease_time).id
        messages.success(request, "Pool requested - id {}".format(pool_id))
    except Exception as e:
        messages.error(request, "Exception {} happened: {}".format(type(e).__name__, str(e)))
    return go_back_or_home(request)


def vms(request, current_provider=None):
    if not request.user.is_authenticated():
        return go_home(request)
    providers = sorted(Provider.get_available_provider_keys())
    if current_provider is None and providers:
        return redirect("vms_at_provider", current_provider=providers[0])
    return render(request, 'appliances/vms/index.html', locals())


def vms_table(request, current_provider=None):
    if not request.user.is_authenticated():
        return go_home(request)
    manager = provider_factory(current_provider)
    vms = sorted(manager.list_vm())
    return render(request, 'appliances/vms/_list.html', locals())


def power_state(request, current_provider):
    vm_name = request.POST["vm_name"]
    manager = provider_factory(current_provider)
    state = Appliance.POWER_STATES_MAPPING.get(manager.vm_status(vm_name), "unknown")
    return HttpResponse(state, content_type="text/plain")


def power_state_buttons(request, current_provider):
    manager = provider_factory(current_provider)
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
        provider_factory(current_provider)
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
