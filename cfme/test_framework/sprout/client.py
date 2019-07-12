# -*- coding: utf-8 -*-
import json
import os

import attr
import requests

from cfme.utils.appliance import current_appliance
from cfme.utils.appliance import IPAppliance
from cfme.utils.conf import credentials
from cfme.utils.conf import env
from cfme.utils.log import logger
from cfme.utils.version import get_stream
from cfme.utils.wait import wait_for
# TODO: use custom wait_for logger fitting sprout


class SproutException(Exception):
    pass


class AuthException(SproutException):
    pass


@attr.s
class APIMethodCall(object):
    _client = attr.ib()
    _method_name = attr.ib()

    def __call__(self, *args, **kwargs):
        return self._client.call_method(self._method_name, *args, **kwargs)


@attr.s
class SproutClient(object):
    _proto = attr.ib(default="http")
    _host = attr.ib(default="localhost")
    _port = attr.ib(default=8000)
    _entry = attr.ib(default="appliances/api")
    _auth = attr.ib(default=None)

    @property
    def api_entry(self):
        return "{}://{}:{}/{}".format(self._proto, self._host, self._port, self._entry)

    def _post(self, **data):
        return requests.post(self.api_entry, data=json.dumps(data))

    def _call_post(self, **data):
        """Protect from the Sprout being updated (error 502,503)"""
        result = wait_for(
            lambda: self._post(**data),
            num_sec=60,
            fail_condition=lambda r: r.status_code in {502, 503},
            delay=2,
        )
        return result.out.json()

    def call_method(self, name, *args, **kwargs):
        req_data = {
            "method": name,
            "args": args,
            "kwargs": kwargs,
        }
        logger.info("SPROUT: Called {} with {} {}".format(name, args, kwargs))
        if self._auth is not None:
            req_data["auth"] = self._auth
        result = self._call_post(**req_data)
        try:
            if result["status"] == "exception":
                raise SproutException(
                    "Exception {} raised! {}".format(
                        result["result"]["class"], result["result"]["message"]))
            elif result["status"] == "autherror":
                raise AuthException(
                    "Authentication failed! {}".format(result["result"]["message"]))
            else:
                return result["result"]
        except KeyError:
            raise Exception("Malformed response from Sprout!")

    def __getattr__(self, attr):
        return APIMethodCall(self, attr)

    @classmethod
    def from_config(cls, **kwargs):
        host = env.get("sprout", {}).get("hostname", "localhost")
        port = env.get("sprout", {}).get("port", 8000)
        user_key = kwargs.pop('sprout_user_key') if 'sprout_user_key' in kwargs else None
        # First choose env var creds, then look in kwargs for a sprout_user_key to lookup
        user = (os.environ.get("SPROUT_USER") or
                (credentials.get(user_key, {}).get("username") if user_key else None))
        password = (os.environ.get("SPROUT_PASSWORD") or
                    (credentials.get(user_key, {}).get("password") if user_key else None))
        if user and password:
            auth = user, password
        else:
            auth = None
        return cls(host=host, port=port, auth=auth, **kwargs)

    def provision_appliances(
            self, count=1, preconfigured=False, version=None, stream=None, provider=None,
            provider_type=None, lease_time=60, ram=None, cpu=None, **kwargs):
        # provisioning may take more time than it is expected in some cases
        wait_time = kwargs.pop('wait_time', 900)
        try:
            wait_time = int(wait_time)
        except ValueError:
            pass

        # If we specify version, stream is ignored because we will get that specific version
        if version:
            stream = get_stream(version)
        # If we specify stream but not version, sprout will give us latest version of that stream
        elif stream:
            pass
        # If we dont specify either, we will get the same version as current appliance
        else:
            stream = get_stream(current_appliance.version)
            version = current_appliance.version.vstring
        request_id = self.call_method(
            'request_appliances',
            preconfigured=preconfigured,
            version=version,
            provider_type=provider_type,
            group=stream,
            provider=provider,
            lease_time=lease_time,
            ram=ram,
            cpu=cpu,
            count=count,
            **kwargs
        )
        wait_for(
            lambda: self.call_method('request_check', str(request_id))['finished'],
            num_sec=wait_time,
            message='provision {} appliance(s) from sprout'.format(count))
        data = self.call_method('request_check', str(request_id))
        logger.debug(data)
        appliances = []
        for appliance in data['appliances']:
            app_args = {'hostname': appliance['ip_address'],
                        'project': appliance['project'],
                        'container': appliance['container'],
                        'db_host': appliance['db_host']}
            appliances.append(IPAppliance(**app_args))
        return appliances, request_id

    def destroy_pool(self, pool_id):
        self.call_method('destroy_pool', id=pool_id)
