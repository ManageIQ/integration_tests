# -*- coding: utf-8 -*-
import inspect
import json
import re
from datetime import datetime
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render

from appliances.models import Appliance, AppliancePool, Provider, Group, Template
from appliances.tasks import appliance_power_on, appliance_power_off, appliance_suspend
from utils.log import create_logger


def api_logger():
    return create_logger("sprout_api")


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


def json_autherror(message):
    return json_response({
        "status": "autherror",
        "result": {
            "message": str(message)
        }
    })


def json_success(result):
    return json_response({
        "status": "success",
        "result": result
    })


class JSONMethod(object):
    def __init__(self, method, auth=False):
        self._method = method
        if self._method.__doc__:
            try:
                head, body = self._method.__doc__.split("\n\n", 1)
                head = head.strip()
                self._doc = head
            except ValueError:
                self._doc = self._method.__doc__.strip()
        else:
            self._doc = ""
        self.auth = auth

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
            "args": f_args if not self.auth else f_args[1:],
            "defaults": defaults,
            "docstring": self._doc,
            "needs_authentication": self.auth,
        }


class JSONApi(object):
    def __init__(self):
        self._methods = {}

    def method(self, f):
        self._methods[f.__name__] = JSONMethod(f)

    def authenticated_method(self, f):
        self._methods[f.__name__] = JSONMethod(f, auth=True)

    def doc(self, request):
        return render(request, 'appliances/apidoc.html', {})

    def __call__(self, request):
        if request.method != 'POST':
            return json_success({
                "available_methods": sorted(
                    map(lambda m: m.description, self._methods.itervalues()),
                    key=lambda m: m["name"]),
            })
        try:
            data = json.loads(request.body)
            method_name = data["method"]
            args = data["args"]
            kwargs = data["kwargs"]
            try:
                method = self._methods[method_name]
            except KeyError:
                raise NameError("Method {} not found!".format(method_name))
            api_logger().info(
                "Calling method {}{}{}".format(method_name, repr(tuple(args)), repr(kwargs)))
            if method.auth:
                if "auth" in data:
                    username, password = data["auth"]
                    try:
                        user = User.objects.get(username=username)
                    except ObjectDoesNotExist:
                        return json_autherror("User {} does not exist!".format(username))
                    if not user.check_password(password):
                        return json_autherror("Wrong password for user {}!".format(username))
                    return json_success(method(user, *args, **kwargs))
                else:
                    return json_autherror("Method {} needs authentication!".format(method_name))
            else:
                return json_success(method(*args, **kwargs))
        except Exception as e:
            api_logger().error(
                "Exception raised during {} call: {}: {}".format(
                    method_name, type(e).__name__, str(e)))
            return json_exception(e)
        else:
            api_logger().info("Call to {} finished".format(method_name))

jsonapi = JSONApi()


def jsonapi_doc(*args, **kwargs):
    return jsonapi.doc(*args, **kwargs)


@jsonapi.method
def list_appliances(used=False):
    """Returns list of appliances.

    Args:
        used: Whether to report used or unused appliances
    """
    query = Appliance.objects
    if used:
        query = query.exclude(appliance_pool__owner=None)
    else:
        query = query.filter(appliance_pool__owner=None)
    result = []
    for appliance in query:
        result.append(appliance.serialized)

    return result


@jsonapi.method
def num_shepherd_appliances(group, version=None, date=None, provider=None):
    """Provides number of currently available shepherd appliances."""
    group = Group.objects.get(id=group)
    if provider is not None:
        provider = Provider.objects.get(id=provider)
    if version is None:
        if provider is None:
            try:
                version = Template.get_versions(template_group=group)[0]
            except IndexError:
                # No version
                pass
        else:
            try:
                version = Template.get_versions(template_group=group, provider=provider)[0]
            except IndexError:
                # No version
                pass
    if date is None:
        filter_kwargs = {"template_group": group}
        if provider is not None:
            filter_kwargs["provider"] = provider
        if version is not None:
            filter_kwargs["version"] = version
        try:
            date = Template.get_dates(**filter_kwargs)[0]
        except IndexError:
            # No date
            pass
    filter_kwargs = {"template__template_group": group, "ready": True, "appliance_pool": None}
    if version is not None:
        filter_kwargs["template__version"] = version
    if date is not None:
        filter_kwargs["template__date"] = date
    if provider is not None:
        filter_kwargs["template__provider"] = provider
    return len(Appliance.objects.filter(**filter_kwargs))


@jsonapi.authenticated_method
def request_appliances(
        user, group, count=1, lease_time=60, version=None, date=None, provider=None,
        preconfigured=True):
    """Request a number of appliances."""
    if date:
        date = datetime.strptime(date, "%y%m%d")
    return AppliancePool.create(
        user, group, version, date, provider, count, lease_time, preconfigured).id


@jsonapi.authenticated_method
def request_check(user, request_id):
    """Return status of the appliance pool"""
    request = AppliancePool.objects.get(id=request_id)
    if user != request.owner and not user.is_staff:
        raise Exception("This pool belongs to a different user!")
    return {
        "fulfilled": request.fulfilled,
        "preconfigured": request.preconfigured,
        "partially_fulfilled": request.partially_fulfilled,
        "progress": int(round(request.percent_finished * 100)),
        "appliances": [
            appliance.serialized
            for appliance
            in request.appliances
        ],
    }


@jsonapi.authenticated_method
def pool_drop_remaining_provisioning_requests(user, request_id):
    """Remove all provisioning requests that are to be executed on the pool"""
    request = AppliancePool.objects.get(id=request_id)
    if user != request.owner and not user.is_staff:
        raise Exception("This pool belongs to a different user!")
    return request.drop_remaining_provisioning_tasks()


@jsonapi.authenticated_method
def prolong_appliance_lease(user, id, minutes=60):
    """Prolongs the appliance's lease time by specified amount of minutes from current time."""
    appliance = Appliance.objects.get(id=id)
    if appliance.owner is not None and user != appliance.owner and not user.is_staff:
        raise Exception("This pool belongs to a different user!")
    appliance.prolong_lease(time=minutes)


@jsonapi.authenticated_method
def prolong_appliance_pool_lease(user, id, minutes=60):
    """Prolongs the appliance pool's lease time by specified amount of minutes from current time."""
    pool = AppliancePool.objects.get(id=id)
    if user != pool.owner and not user.is_staff:
        raise Exception("This pool belongs to a different user!")
    pool.prolong_lease(time=minutes)


@jsonapi.authenticated_method
def destroy_pool(user, id):
    """Destroy the pool. Kills all associated appliances."""
    pool = AppliancePool.objects.get(id=id)
    if user != pool.owner and not user.is_staff:
        raise Exception("This pool belongs to a different user!")
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


@jsonapi.authenticated_method
def set_number_free_appliances(user, group, n):
    """Set number of available appliances to keep in the pool"""
    if not user.is_staff:
        raise Exception("You don't have enough rights!")
    if n < 0:
        return False
    with transaction.atomic():
        g = Group.objects.get(id=group)
        g.template_pool_size = n
        g.save()
        return True


@jsonapi.method
def available_cfme_versions(preconfigured=True):
    """Lists all versions that are available"""
    return Template.get_versions(preconfigured=preconfigured)


@jsonapi.method
def available_groups():
    return map(lambda group: group.id, Group.objects.all())


@jsonapi.method
def available_providers():
    return map(lambda group: group.id, Provider.objects.all())


@jsonapi.authenticated_method
def add_provider(user, provider_key):
    if not user.is_staff:
        raise Exception("You don't have enough rights!")
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


@jsonapi.authenticated_method
def destroy_appliance(user, appliance):
    """Destroy the appliance.

    You can specify appliance by IP address, id or name.
    """
    appliance = get_appliance(appliance)
    if appliance.owner is None:
        if not user.is_staff:
            raise Exception("Only staff can operate with nonowned appliances")
    elif appliance.owner != user:
        raise Exception("This appliance belongs to a different user!")
    Appliance.kill(appliance)
    return True


@jsonapi.method
def power_state(appliance):
    """Return appliance's current power state.

    You can specify appliance by IP address, id or name.
    """
    return get_appliance(appliance).power_state


@jsonapi.authenticated_method
def power_on(user, appliance):
    """Power on the appliance

    You can specify appliance by IP address, id or name.
    """
    appliance = get_appliance(appliance)
    if appliance.owner is None:
        if not user.is_staff:
            raise Exception("Only staff can operate with nonowned appliances")
    elif appliance.owner != user:
        raise Exception("This appliance belongs to a different user!")
    if appliance.power_state != Appliance.Power.ON:
        appliance_power_on.delay(appliance.id)
    return True


@jsonapi.authenticated_method
def power_off(user, appliance):
    """Power off the appliance

    You can specify appliance by IP address, id or name.
    """
    appliance = get_appliance(appliance)
    if appliance.owner is None:
        if not user.is_staff:
            raise Exception("Only staff can operate with nonowned appliances")
    elif appliance.owner != user:
        raise Exception("This appliance belongs to a different user!")
    if appliance.power_state != Appliance.Power.OFF:
        appliance_power_off.delay(appliance.id)
    return True


@jsonapi.authenticated_method
def suspend(user, appliance):
    """Suspend the appliance

    You can specify appliance by IP address, id or name.
    """
    appliance = get_appliance(appliance)
    if appliance.owner is None:
        if not user.is_staff:
            raise Exception("Only staff can operate with nonowned appliances")
    elif appliance.owner != user:
        raise Exception("This appliance belongs to a different user!")
    if appliance.power_state == Appliance.Power.OFF:
        return False
    elif appliance.power_state != Appliance.Power.SUSPENDED:
        appliance_suspend.delay(appliance.id)
    return True


@jsonapi.authenticated_method
def set_pool_description(user, pool_id, description):
    """Set the pool's description"""
    pool = AppliancePool.objects.get(id=pool_id)
    if pool.owner is None:
        if not user.is_staff:
            raise Exception("Only staff can operate with nonowned appliances")
    elif pool.owner != user:
        raise Exception("This appliance belongs to a different user!")
    pool.description = description
    pool.save()
    return True


@jsonapi.authenticated_method
def get_pool_description(user, pool_id):
    """Get the pool's description"""
    pool = AppliancePool.objects.get(id=pool_id)
    if pool.owner is None:
        if not user.is_staff:
            raise Exception("Only staff can operate with nonowned appliances")
    elif pool.owner != user:
        raise Exception("This appliance belongs to a different user!")
    return pool.description


@jsonapi.authenticated_method
def find_pools_by_description(user, description, partial=False):
    """Searches pools to find a pool with matching descriptions. When partial, `in` is used"""
    pools = []
    for pool in AppliancePool.objects.all():
        if not pool.description:
            continue
        if partial:
            if description in pool.description:
                pools.append(pool)
        else:
            if pool.description == description:
                pools.append(pool)

    def _filter(pool):
        return (pool.owner is None and user.is_staff) or (pool.owner == user)

    return map(lambda pool: pool.id, filter(_filter, pools))
