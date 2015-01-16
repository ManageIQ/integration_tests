# -*- coding: utf-8 -*-
import json
import os
import requests

from utils.conf import cfme_data, credentials
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

    def wait_for_sprout_available(self, minutes=5):
        wait_for(
            lambda: requests.get(self.api_entry).status_code == 200,
            num_sec=60 * minutes, delay=5, message="Sprout becomes available")

    def call_method(self, name, *args, **kwargs):
        req_data = {
            "method": name,
            "args": args,
            "kwargs": kwargs,
        }
        if self._auth is not None:
            req_data["auth"] = self._auth
        result = requests.post(self.api_entry, data=json.dumps(req_data)).json()
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
        host = cfme_data.get("sprout", {}).get("hostname", "localhost")
        port = cfme_data.get("sprout", {}).get("port", 8000)
        user = os.environ.get("SPROUT_USER", credentials.get("sprout", {}).get("username", None))
        password = os.environ.get(
            "SPROUT_PASSWORD", credentials.get("sprout", {}).get("password", None))
        if user and password:
            auth = user, password
        else:
            auth = None
        return cls(host=host, port=port, auth=auth, **kwargs)
