#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Cleanup unused instance snapshot from glance repository

Usage: scripts/cleanup_openstack_instance_snapshot.py [optional list of provider keys]

If no providers specified, it will cleanup all of them.

"""
import sys
from datetime import datetime
from datetime import timedelta

import iso8601
import tzlocal

from cfme.utils.providers import get_mgmt
from cfme.utils.providers import list_provider_keys

local_tz = tzlocal.get_localzone()
GRACE_TIME = timedelta(hours=2)
time_limit = datetime.now(tz=local_tz) - GRACE_TIME


def main(*providers):
    for provider_key in providers:
        print("Cleaning up {}".format(provider_key))
        api = get_mgmt(provider_key).gapi
        try:
            images = api.images.list()
        except Exception as e:
            print("Connect to provider failed:{} {} {}".format(
                provider_key, type(e).__name__, str(e)))
            continue

        for img in images:
            if "test_snapshot_" in img.name \
                    and iso8601.parse_date(img.created_at) < time_limit:
                print("Deleting {}".format(img.name))
                try:
                    api.images.delete(img.id)
                except Exception as e:
                    print("Delete failed: {} {}".format(type(e).__name__, str(e)))


if __name__ == "__main__":
    provs = sys.argv[1:]
    if provs:
        main(*provs)
    else:
        main(*list_provider_keys("openstack"))
