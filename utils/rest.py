# -*- coding: utf-8 -*-
import requests

from utils.conf import credentials, env


def GET(loc, **params):
    url = env["base_url"]
    while loc.startswith("/"):
        loc = loc[1:]
    result = requests.get(
        "{}/api/{}/{}".format(url, env["api_version"], loc),
        verify=False,
        auth=(credentials["default"]["username"], credentials["default"]["password"]),
        headers={"Accept": "application/json"},
        params=params).json()
    if "error" in result:
        raise Exception("{}: {}".format(result["error"]["kind"], result["error"]["message"]))
    return result
