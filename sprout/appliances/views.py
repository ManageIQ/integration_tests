# -*- coding: utf-8 -*-
import json
import xmlrpclib
from functools import wraps

from celery import chain
from celery.result import AsyncResult
from dateutil import parser
from django.contrib import messages
from django.contrib.auth import views
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.shortcuts import render, redirect

from appliances.api import json_response
from appliances.models import (
    Provider, AppliancePool, Appliance, Group, Template, MismatchVersionMailer, User, BugQuery,
    GroupShepherd)
from appliances.tasks import (appliance_power_on, appliance_power_off, appliance_suspend,
    anyvm_power_on, anyvm_power_off, anyvm_suspend, anyvm_delete, delete_template_from_provider,
    appliance_rename, wait_appliance_ready, mark_appliance_ready, appliance_reboot)

from sprout.log import create_logger
from cfme.utils.bz import Bugzilla
from cfme.utils.providers import get_mgmt
from cfme.utils.version import Version


def go_home(request):
    return redirect(index)


def go_back_or_home(request):
    ref = request.META.get('HTTP_REFERER')
    if ref:
        return redirect(ref)
    else:
        return go_home(request)


def only_authenticated(view):
    @wraps(view)
    def g(request, *args, **kwargs):
        if not request.user.is_authenticated():
            messages.error(
                request, 'You need to be authenticated to access "{}"'.format(request.path))
            return go_home(request)
        else:
            return view(request, *args, **kwargs)

    if not hasattr(g, '__wrapped__'):
        g.__wrapped__ = view
    return g


def logout(request):
    views.logout(request)
    messages.info(request, 'You have been logged out')
    return go_home(request)


def index(request):
    superusers = User.objects.filter(is_superuser=True).order_by("last_name", "first_name")
    return render(request, 'index.html', locals())


def providers(request, provider_id=None):
    if request.user.is_staff or request.user.is_superuser:
        user_filter = {}
    else:
        user_filter = {'user_groups__in': request.user.groups.all()}
    if provider_id is None:
        try:
            provider = Provider.objects.filter(hidden=False, **user_filter).order_by("id")[0]
            return redirect(
                "specific_provider",
                provider_id=provider.id)
        except IndexError:
            # No Provider
            messages.info(request, "No provider present, redirected to the homepage.")
            return go_home(request)
    else:
        try:
            provider = Provider.objects.filter(id=provider_id, **user_filter).distinct().first()
            if provider is None:
                messages.error(
                    request,
                    'Could not find a provider with name {} that you would have access to.'.format(
                        provider_id))
                return go_home(request)
            if provider.hidden:
                messages.warning(request, 'Provider {} is hidden.'.format(provider_id))
                return redirect('providers')
        except ObjectDoesNotExist:
            messages.warning(request, "Provider '{}' does not exist.".format(provider_id))
            return redirect("providers")
    providers = Provider.objects.filter(hidden=False, **user_filter).order_by("id").distinct()
    return render(request, 'appliances/providers.html', locals())


def provider_usage(request):
    complete_usage = Provider.complete_user_usage(request.user)
    return render(request, 'appliances/provider_usage.html', locals())


def templates(request, group_id=None, prov_id=None):
    if request.user.is_staff or request.user.is_superuser:
        user_filter = {}
        user_filter_2 = {}
    else:
        user_filter = {'user_groups__in': request.user.groups.all()}
        user_filter_2 = {'provider__user_groups__in': request.user.groups.all()}
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
            provider = Provider.objects.filter(id=prov_id, **user_filter).distinct().first()
        except ObjectDoesNotExist:
            messages.warning(request, "Provider '{}' does not exist.".format(prov_id))
            return redirect("templates")
    else:
        provider = None
    if provider is not None:
        user_filter_2 = {'provider': provider}
    groups = Group.objects.order_by("id")
    mismatched_versions = MismatchVersionMailer.objects.order_by("id")
    prepared_table = []
    zstream_rowspans = {}
    version_rowspans = {}
    date_version_rowspans = {}
    items = group.zstreams_versions.items()
    items.sort(key=lambda pair: Version(pair[0]), reverse=True)
    for zstream, versions in items:
        for version in versions:
            for template in Template.objects.filter(
                    template_group=group, version=version, exists=True,
                    ready=True, **user_filter_2).order_by('-date', 'provider').distinct():
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

                datetuple = (template.date, version)
                if datetuple in date_version_rowspans:
                    date_version_rowspans[datetuple] += 1
                    date_append = None
                else:
                    date_version_rowspans[datetuple] = 1
                    date_append = template.date
                prepared_table.append((
                    zstream_append, version_append, date_append, datetuple, template.provider,
                    template))
    return render(request, 'appliances/templates.html', locals())


@only_authenticated
def shepherd(request):
    groups = Group.objects.all()
    shepherds = GroupShepherd.objects.filter(
        template_group__in=groups, user_group__in=request.user.groups.all()).distinct().order_by(
        'template_group__id')
    return render(request, 'appliances/shepherd.html', locals())


@only_authenticated
def versions_for_group(request):
    if not request.user.is_authenticated():
        return go_home(request)
    group_id = request.POST.get("stream")
    latest_version = None
    preconfigured = request.POST.get("preconfigured", "false").lower() == "true"
    container = request.POST.get("container", "false").lower() == "true"
    container_q = ~Q(container=None) if container else Q(container=None)
    if group_id == "<None>":
        versions = []
        group = None
    else:
        try:
            group = Group.objects.get(id=group_id)
        except ObjectDoesNotExist:
            versions = []
        else:
            versions = [
                (version, Template.ga_version(version))
                for version in Template.get_versions(
                    container_q,
                    template_group=group, ready=True, usable=True, exists=True,
                    preconfigured=preconfigured, provider__working=True, provider__disabled=False,
                    provider__user_groups__in=request.user.groups.all())]
            if versions:
                if versions[0][1]:
                    latest_version = '{} (GA)'.format(versions[0][0])
                else:
                    latest_version = versions[0][0]

    return render(request, 'appliances/_versions.html', locals())


@only_authenticated
def date_for_group_and_version(request):
    if not request.user.is_authenticated():
        return go_home(request)
    group_id = request.POST.get("stream")
    latest_date = None
    preconfigured = request.POST.get("preconfigured", "false").lower() == "true"
    container = request.POST.get("container", "false").lower() == "true"
    container_q = ~Q(container=None) if container else Q(container=None)
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
                'provider__disabled': False,
                "provider__user_groups__in": request.user.groups.all(),
            }
            if version == "latest":
                try:
                    versions = Template.get_versions(container_q, **filters)
                    filters["version"] = versions[0]
                except IndexError:
                    pass  # No such thing as version for this template group
            else:
                filters["version"] = version
            dates = Template.get_dates(container_q, **filters)
            if dates:
                latest_date = dates[0]
    return render(request, 'appliances/_dates.html', locals())


@only_authenticated
def providers_for_date_group_and_version(request):
    if not request.user.is_authenticated():
        return go_home(request)
    total_provisioning_slots = 0
    total_appliance_slots = 0
    total_shepherd_slots = 0
    shepherd_appliances = {}
    group_id = request.POST.get("stream")
    preconfigured = request.POST.get("preconfigured", "false").lower() == "true"
    container = request.POST.get("container", "false").lower() == "true"
    container_q = ~Q(container=None) if container else Q(container=None)
    if container:
        appliance_container_q = ~Q(template__container=None)
    else:
        appliance_container_q = Q(template__container=None)
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
                "provider__disabled": False,
                "provider__user_groups__in": request.user.groups.all(),
            }
            if version == "latest":
                try:
                    versions = Template.get_versions(container_q, **filters)
                    filters["version"] = versions[0]
                except IndexError:
                    pass  # No such thing as version for this template group
            else:
                filters["version"] = version
            date = request.POST.get("date")
            if date == "latest":
                try:
                    dates = Template.get_dates(container_q, **filters)
                    filters["date"] = dates[0]
                except IndexError:
                    pass  # No such thing as date for this template group
            else:
                filters["date"] = parser.parse(date)
            providers = Template.objects.filter(
                container_q, **filters).values("provider").distinct()
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
                shepherd_appliances[provider.id] = len(
                    Appliance.objects.filter(appliance_container_q, **appl_filter))
                total_shepherd_slots += shepherd_appliances[provider.id]
                total_appliance_slots += provider.remaining_appliance_slots
                total_provisioning_slots += provider.remaining_provisioning_slots

            render_providers = {}
            for provider in providers:
                render_providers[provider.id] = {
                    "shepherd_count": shepherd_appliances[provider.id], "object": provider}
    return render(request, 'appliances/_providers.html', locals())


@only_authenticated
def my_appliances(request, show_user="my"):
    if not request.user.is_superuser:
        if not (show_user == "my" or show_user == request.user.username):
            messages.info(request, "You can't view others' appliances!")
            return redirect("my_appliances")
        if show_user == request.user.username:
            return redirect("my_appliances")
    else:
        other_users = User.objects.exclude(pk=request.user.pk).order_by("last_name", "first_name")
    if show_user == "my":
        pools = AppliancePool.objects.filter(owner=request.user).order_by("id")
    elif show_user == "all":
        pools = AppliancePool.objects.order_by("id")
    else:
        pools = AppliancePool.objects.filter(owner__username=show_user).order_by("id")
    page = request.GET.get("page")
    try:
        per_page = int(request.GET.get("per_page", 5))
    except (ValueError, TypeError):
        per_page = 5

    pools_paginator = Paginator(pools, per_page)
    try:
        pools_paged = pools_paginator.page(page)
        page = int(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        pools_paged = pools_paginator.page(1)
        page = 1
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        pools_paged = pools_paginator.page(pools_paginator.num_pages)
        page = pools_paginator.num_pages

    pages = list(pools_paginator.page_range)
    if pools_paginator.num_pages <= 5:
        start_index = 0
        end_index = 5
    else:
        if page - 2 < 0:
            start_index = 0
            end_index = 5
        elif page + 2 > pools_paginator.num_pages:
            end_index = pools_paginator.num_pages
            start_index = end_index - 5
        else:
            start_index = page - 3
            end_index = page + 2
    if start_index < 0:
        end_index -= start_index
        start_index = 0
    pages = pages[start_index:end_index]
    available_groups = Group.objects.filter(
        id__in=Template.objects.values_list('template_group', flat=True).distinct())
    group_tuples = []
    for group in available_groups:
        group_tuples.append((group.templates.order_by('-date')[0].date, group))
    group_tuples.sort(key=lambda gt: gt[0], reverse=True)
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
    can_change_hw = request.user.has_perm('appliances.can_modify_hw')
    return render(request, 'appliances/my_appliances.html', locals())


def can_operate_appliance_or_pool(appliance_or_pool, user):
    if user.is_superuser:
        return True
    else:
        return appliance_or_pool.owner == user


@only_authenticated
def appliance_action(request, appliance_id, action, x=None):
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
                mark_appliance_ready.si(appliance.id))()
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


@only_authenticated
def prolong_lease_pool(request, pool_id, minutes):
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


@only_authenticated
def dont_expire_pool(request, pool_id):
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


@only_authenticated
def kill_pool(request, pool_id):
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


@only_authenticated
def delete_pool(request, pool_id):
    try:
        pool = AppliancePool.objects.get(id=pool_id)
    except ObjectDoesNotExist:
        messages.warning(request, 'Pool with ID {} does not exist!.'.format(pool_id))
        return go_back_or_home(request)
    if not can_operate_appliance_or_pool(pool, request.user):
        messages.warning(request, 'This pool belongs either to some other user or nobody.')
        return go_back_or_home(request)
    try:
        pool.delete()
    except Exception as e:
        messages.warning(request, "Exception {}: {}".format(type(e).__name__, str(e)))
    else:
        messages.success(request, 'Deleted.')
    return go_back_or_home(request)


def set_pool_description(request):
    if not request.user.is_authenticated():
        raise PermissionDenied()
    try:
        pool_id = request.POST.get("pool_id")
        pool = AppliancePool.objects.get(id=pool_id)
    except ObjectDoesNotExist:
        raise Http404('Pool with ID {} does not exist!.'.format(pool_id))
    if not can_operate_appliance_or_pool(pool, request.user):
        raise PermissionDenied()
    description = request.POST.get("description")
    pool.description = description
    pool.save()
    return HttpResponse("")


def delete_template_provider(request):
    if not request.user.is_authenticated() or not request.user.is_superuser:
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


@only_authenticated
def clone_pool(request):
    try:
        count = int(request.POST["count"])
        source_pool_id = int(request.POST["source_pool_id"])
        pool = AppliancePool.objects.get(id=source_pool_id)
        result_pool = pool.clone(num_appliances=count, owner=request.user)
        messages.success(request, "Pool cloned - id {}".format(result_pool.id))
    except Exception as e:
        messages.warning(request, "{}: {}".format(type(e).__name__, e))
    return go_back_or_home(request)


@only_authenticated
def request_pool(request):
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
        container = request.POST.get("container", "false").lower() == "true"
        if container:
            # Container is preconfigured only
            # We need to do this as the disabled checkbox for Preconfigured seems to not return
            # the proper value.
            preconfigured = True
        count = int(request.POST["count"])
        lease_time = int(request.POST.get("expiration", 60))
        ram = None
        cpu = None
        if request.user.has_perm('appliances.can_modify_hw'):
            if 'ram' in request.POST:
                ram = int(request.POST['ram'])
            if 'cpu' in request.POST:
                cpu = int(request.POST['cpu'])
        pool_id = AppliancePool.create(
            request.user, group, version, date, provider, count, lease_time, preconfigured,
            yum_update, container, ram, cpu).id
        messages.success(request, "Pool requested - id {}".format(pool_id))
    except Exception as e:
        messages.warning(request, "{}: {}".format(type(e).__name__, e))
    return go_back_or_home(request)


@only_authenticated
def transfer_pool(request):
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
    if not request.user.is_authenticated() or not request.user.is_superuser:
        return go_home(request)
    all_provider_keys = sorted(Provider.get_available_provider_keys())
    providers = []
    provider_keys = []
    if request.user.is_staff or request.user.is_superuser:
        user_filter = {}
    else:
        user_filter = {'user_groups__in': request.user.groups.all()}
    for provider_key in all_provider_keys:
        try:
            provider = Provider.objects.filter(id=provider_key, **user_filter).distinct().first()
        except ObjectDoesNotExist:
            continue
        if provider is not None:
            providers.append((provider_key, provider.is_working))
            provider_keys.append(provider_key)
    if current_provider is None and providers:
        return redirect("vms_at_provider", current_provider=provider_keys[0])
    return render(request, 'appliances/vms/index.html', locals())


def vms_table(request, current_provider=None):
    if not request.user.is_authenticated() or not request.user.is_superuser:
        return go_home(request)
    try:
        manager = get_mgmt(current_provider)
        vms = sorted(manager.list_vm())
        return render(request, 'appliances/vms/_list.html', locals())
    except Exception as e:
        return HttpResponse('{}: {}'.format(type(e).__name__, str(e)), content_type="text/plain")


def power_state(request, current_provider):
    if not request.user.is_authenticated() or not request.user.is_superuser:
        return go_home(request)
    vm_name = request.POST["vm_name"]
    manager = get_mgmt(current_provider)
    state = Appliance.POWER_STATES_MAPPING.get(manager.vm_status(vm_name), "unknown")
    return HttpResponse(state, content_type="text/plain")


def power_state_buttons(request, current_provider):
    if not request.user.is_authenticated() or not request.user.is_superuser:
        return go_home(request)
    manager = get_mgmt(current_provider)
    vm_name = request.POST["vm_name"]
    power_state = request.POST["power_state"]
    can_power_on = power_state in {Appliance.Power.SUSPENDED, Appliance.Power.OFF}
    can_power_off = power_state in {Appliance.Power.ON}
    can_suspend = power_state in {Appliance.Power.ON} and manager.can_suspend
    can_delete = power_state in {Appliance.Power.OFF}
    return render(request, 'appliances/vms/_buttons.html', locals())


def vm_action(request, current_provider):
    if not request.user.is_authenticated() or not request.user.is_superuser:
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


def check_appliance(request, provider_id, appliance_name):
    try:
        appliance = Appliance.objects.get(name=appliance_name, template__provider=provider_id)
    except ObjectDoesNotExist:
        return json_response(None)
    owner = appliance.owner
    if owner is not None:
        owner = owner.username
    data = {
        'stream': appliance.template.template_group.id,
        'version': appliance.template.version,
        'date': appliance.template.date.strftime('%Y-%m-%d'),
        'preconfigured': appliance.template.preconfigured,
        'owner': owner,
    }
    return json_response(data)


def check_template(request, provider_id, template_name):
    try:
        template = Template.objects.get(name=template_name, provider=provider_id)
    except ObjectDoesNotExist:
        return json_response(None)
    data = {
        'stream': template.template_group.id,
        'version': template.version,
        'date': template.date.strftime('%Y-%m-%d'),
        'preconfigured': template.preconfigured,
    }
    return json_response(data)


def check_pool(request, pool_id):
    try:
        pool = AppliancePool.objects.get(id=pool_id)
    except ObjectDoesNotExist:
        return json_response(None)
    data = {
        'description': pool.description,
        'stream': pool.group.id,
        'version': pool.version,
        'date': pool.date.strftime('%Y-%m-%d'),
        'preconfigured': pool.preconfigured,
        'finished': pool.finished,
        'owner': pool.owner.username,
        'appliances': [[a.name, a.template.provider.id] for a in pool.appliances]
    }
    return json_response(data)


def check_pools(request):
    data = []
    for pool in AppliancePool.objects.all():
        pool_data = {
            'description': pool.description,
            'id': pool.id,
            'stream': pool.group.id,
            'version': pool.version,
            'date': pool.date.strftime('%Y-%m-%d'),
            'preconfigured': pool.preconfigured,
            'finished': pool.finished,
            'owner': pool.owner.username,
            'appliances': [[a.name, a.template.provider.id] for a in pool.appliances]
        }
        data.append(pool_data)
    return json_response(data)


def view_bug_query(request, query_id):
    if not request.user.is_authenticated():
        return go_home(request)
    queries = BugQuery.visible_for_user(request.user)
    query = BugQuery.objects.get(id=query_id)
    if query.owner is not None and query.owner != request.user:
        if not request.user.is_superuser:
            messages.info(request, "You cannot view BugQuery {}.".format(query.id))
            return go_home(request)
    try:
        bugs = query.list_bugs(request.user)
    except xmlrpclib.Fault as e:
        messages.error(request, 'Bugzilla query error {}: {}'.format(e.faultCode, e.faultString))
        return go_home(request)
    return render(request, 'bugs/list_query.html', locals())


def view_bug_queries(request):
    if not request.user.is_authenticated():
        return go_home(request)
    try:
        first_query = BugQuery.visible_for_user(request.user)[0]
    except IndexError:
        first_query = None
    if first_query is not None:
        return redirect('view_bug_query', first_query.id)
    else:
        # No Group
        messages.info(request, "No query present, redirected to the homepage.")
        return go_home(request)


def new_bug_query(request):
    if not request.user.is_authenticated():
        return go_home(request)
    queries = BugQuery.visible_for_user(request.user)
    query = None
    if request.method == 'GET':
        return render(request, 'bugs/new_query.html', locals())
    elif request.method != 'POST':
        messages.error(request, "Invalid request.")
        return go_home(request)
    # Create a new one
    name = request.POST['name']
    url = request.POST['url']
    global_ = request.POST.get('global', 'false') == 'true'
    if not request.user.is_superuser:
        global_ = False
    if global_:
        owner = None
    else:
        owner = request.user
    bug_query = BugQuery(name=name, url=url, owner=owner)
    bug_query.save()
    messages.info(request, "Query with name {} added.".format(name))
    return redirect('view_bug_query', bug_query.id)


def delete_bug_query(request, query_id):
    if not request.user.is_authenticated():
        return go_home(request)
    query = BugQuery.objects.get(id=query_id)
    if query.owner == request.user or request.user.is_superuser:
        query.delete()
        messages.info(request, "Query with name {} deleted.".format(query.name))
        return redirect('view_bug_queries')
    else:
        messages.error(request, "You cannot delete query with name {}.".format(query.name))
        return redirect('view_bug_queries')


def check_query(request):
    if not request.user.is_authenticated():
        return go_home(request)
    if request.method != 'POST':
        return HttpResponseForbidden('Only POST allowed')
    bz = Bugzilla.from_config().bugzilla
    try:
        parsed = bz.url_to_query(request.POST['url'])
        if not parsed:
            parsed = None
    except:
        parsed = None
    if 'cmdtype' in parsed:
        # It is a command and that is not supported within .query()
        parsed = None
    return json_response(parsed)


def swap_offenders(request):
    appliances = Appliance.objects.filter(
        power_state=Appliance.Power.ON).exclude(Q(swap=None) | Q(swap=0)).order_by('-swap')[:15]
    failed_ssh = Appliance.objects.filter(ssh_failed=True, power_state=Appliance.Power.ON).order_by(
        'appliance_pool__owner__username', 'name')
    return render(request, 'appliances/swap_offenders.html', locals())
