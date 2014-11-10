# -*- coding: utf-8 -*-
import json
import requests

from utils.conf import cfme_data


class SproutException(Exception):
    pass


class APIMethodCall(object):
    def __init__(self, client, method_name):
        self._client = client
        self._method_name = method_name

    def __call__(self, *args, **kwargs):
        return self._client.call_method(self._method_name, *args, **kwargs)


class SproutClient(object):
    def __init__(self, protocol="http", host="localhost", port=8000, entry="appliances/api"):
        self._proto = protocol
        self._host = host
        self._port = port
        self._entry = entry

    @property
    def api_entry(self):
        return "{}://{}:{}/{}".format(self._proto, self._host, self._port, self._entry)

    def call_method(self, name, *args, **kwargs):
        result = requests.post(self.api_entry, data=json.dumps({
            "method": name,
            "args": args,
            "kwargs": kwargs,
        })).json()
        try:
            if result["status"] == "exception":
                raise SproutException(
                    "Exception {} raised! {}".format(
                        result["result"]["class"], result["result"]["message"]))
            else:
                return result["result"]
        except KeyError:
            raise Exception("Malformed response from Sprout!")

    def __getattr__(self, attr):
        return APIMethodCall(self, attr)

    @classmethod
    def from_config(cls):
        host = cfme_data.get("sprout", {}).get("hostname", "localhost")
        port = cfme_data.get("sprout", {}).get("port", 8000)

        return cls(host=host, port=port)
