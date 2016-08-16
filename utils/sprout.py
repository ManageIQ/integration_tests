# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import os
import requests

from utils.conf import credentials, env
from utils.wait import wait_for


class SproutException(Exception):
    pass


class AuthException(SproutException):
    pass


class APIMethodCall(object):
    def __init__(self, client, method_name):
        self._client = client
        self._method_name = method_name

    def __call__(self, *args, **kwargs):
        return self._client.call_method(self._method_name, *args, **kwargs)


class SproutClient(object):
    def __init__(
            self, protocol="http", host="localhost", port=8000, entry="appliances/api", auth=None):
        self._proto = protocol
        self._host = host
        self._port = port
        self._entry = entry
        self._auth = auth

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
        user = os.environ.get("SPROUT_USER", credentials.get("sprout", {}).get("username", None))
        password = os.environ.get(
            "SPROUT_PASSWORD", credentials.get("sprout", {}).get("password", None))
        if user and password:
            auth = user, password
        else:
            auth = None
        return cls(host=host, port=port, auth=auth, **kwargs)
