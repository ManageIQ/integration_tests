# -*- coding: utf-8 -*-
import inspect
import json
import re
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render

from appliances.models import Appliance, AppliancePool, Provider, Group, Template
from appliances.tasks import appliance_power_on, appliance_power_off, appliance_suspend


def json_response(data):
    return HttpResponse(json.dumps(data), content_type="application/json")


def json_exception(e):
    return json_response({
        "status": "exception",
        "result": {
            "class": type(e).__name__,
            "message": str(e)
        }
    })


def json_success(result):
    return json_response({
        "status": "success",
        "result": result
    })


class JSONMethod(object):
    def __init__(self, method):
        self._method = method

    def __call__(self, *args, **kwargs):
        return self._method(*args, **kwargs)

    @property
    def description(self):
        f_args = inspect.getargspec(self._method).args
        f_defaults = inspect.getargspec(self._method).defaults
        defaults = {}
        if f_defaults is not None:
            for key, value in zip(f_args[-len(f_defaults):], f_defaults):
                defaults[key] = value
        return {
            "name": self._method.__name__,
            "args": f_args,
            "defaults": defaults,
            "docstring": self._method.__doc__ or "",
        }


class JSONApi(object):
    def __init__(self):
        self._methods = {}

    def method(self, f):
        self._methods[f.__name__] = JSONMethod(f)

    def doc(self, request):
        return render(request, 'appliances/apidoc.html', {})

    def __call__(self, request):
        if request.method != 'POST':
            return json_success({
                "available_methods": map(lambda m: m.description, self._methods.itervalues()),
            })
        try:
            data = json.loads(request.body)
            method_name = data["method"]
            args = data["args"]
            kwargs = data["kwargs"]
            return json_success(self._methods[method_name](*args, **kwargs))
        except Exception as e:
            return json_exception(e)

jsonapi = JSONApi()


def apply_if_not_none(o, meth, *args, **kwargs):
    if o is None:
        return None
    return getattr(o, meth)(*args, **kwargs)


@jsonapi.method
def request_appliances(
        group, count=1, lease_time=60, template=None, provider=None, version=None, date=None):
    """Request a number of appliances."""
    if date:
        date = datetime.strptime(date, "%y%m%d")
    return AppliancePool.create(group, version, date, count, lease_time).id


@jsonapi.method
def request_check(request_id):
    """Return status of the appliance pool"""
    request = AppliancePool.objects.get(id=request_id)
    return {
        "fulfilled": request.fulfilled,
        "appliances": [
            dict(
                id=appliance.id,
                ready=appliance.ready,
                name=appliance.name,
                ip_address=appliance.ip_address,
                status=appliance.status,
                power_state=appliance.power_state,
                status_changed=apply_if_not_none(appliance.status_changed, "isoformat"),
                datetime_leased=apply_if_not_none(appliance.datetime_leased, "isoformat"),
                leased_until=apply_if_not_none(appliance.leased_until, "isoformat"),
            )
            for appliance
            in request.appliances
        ],
    }


@jsonapi.method
def prolong_appliance_lease(id, minutes=60):
    """Prolongs the appliance's lease time by specified amount of minutes from current time."""
    appliance = Appliance.objects.get(id=id)
    appliance.prolong_lease(time=minutes)


@jsonapi.method
def prolong_appliance_pool_lease(id, minutes=60):
    """Prolongs the appliance pool's lease time by specified amount of minutes from current time."""
    pool = AppliancePool.objects.get(id=id)
    pool.prolong_lease(time=minutes)


@jsonapi.method
def destroy_pool(id):
    """Destroy the pool. Kills all associated appliances."""
    pool = AppliancePool.objects.get(id=id)
    pool.kill()


@jsonapi.method
def pool_exists(id):
    """Check whether pool does exist"""
    try:
        AppliancePool.objects.get(id=id)
        return True
    except ObjectDoesNotExist:
        return False


@jsonapi.method
def get_number_free_appliances(group):
    """Get number of available appliances to keep in the pool"""
    with transaction.atomic():
        g = Group.objects.get(id=group)
        return g.template_pool_size


@jsonapi.method
def set_number_free_appliances(group, n):
    """Set number of available appliances to keep in the pool"""
    if n < 0:
        return False
    with transaction.atomic():
        g = Group.objects.get(id=group)
        g.template_pool_size = n
        g.save()
        return True


@jsonapi.method
def available_cfme_versions():
    return Template.get_versions()


@jsonapi.method
def available_groups():
    return map(lambda group: group.id, Group.objects.all())


@jsonapi.method
def available_providers():
    return map(lambda group: group.id, Provider.objects.all())


@jsonapi.method
def add_provider(provider_key):
    try:
        provider_o = Provider.objects.get(id=provider_key)
        return False
    except ObjectDoesNotExist:
        provider_o = Provider(id=provider_key)
        provider_o.save()
        return True


def get_appliance(appliance):
    """'Multimethod' that receives an object and tries to guess by what field the appliance
    should be retrieved. Then it retrieves the appliance"""
    if isinstance(appliance, int):
        return Appliance.objects.get(id=appliance)
    elif re.match(r"^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$", appliance) is not None:
        return Appliance.objects.get(ip_address=appliance)
    else:
        return Appliance.objects.get(name=appliance)


@jsonapi.method
def destroy_appliance(appliance):
    """Destroy the appliance.

    You can specify appliance by IP address, id or name.
    """
    Appliance.kill(get_appliance(appliance))
    return True


@jsonapi.method
def power_state(appliance):
    """Return appliance's current power state.

    You can specify appliance by IP address, id or name.
    """
    return get_appliance(appliance).power_state


@jsonapi.method
def power_on(appliance):
    """Power on the appliance

    You can specify appliance by IP address, id or name.
    """
    appliance = get_appliance(appliance)
    if appliance.power_state != Appliance.Power.ON:
        appliance_power_on.delay(appliance.id)
    return True


@jsonapi.method
def power_off(appliance):
    """Power off the appliance

    You can specify appliance by IP address, id or name.
    """
    appliance = get_appliance(appliance)
    if appliance.power_state != Appliance.Power.OFF:
        appliance_power_off.delay(appliance.id)
    return True


@jsonapi.method
def suspend(appliance):
    """Suspend the appliance

    You can specify appliance by IP address, id or name.
    """
    appliance = get_appliance(appliance)
    if appliance.power_state == Appliance.Power.OFF:
        return False
    elif appliance.power_state != Appliance.Power.SUSPENDED:
        appliance_suspend.delay(appliance.id)
    return True
