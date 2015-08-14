#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Cleanup unattached volumes

Usage: scripts/cleanup_openstack_volumes.py [optional list of provider keys]

If no providers specified, it will cleanup all of them.

"""
import sys
import iso8601
import tzlocal
from datetime import datetime, timedelta

from utils.providers import list_providers, get_mgmt

local_tz = tzlocal.get_localzone()
GRACE_TIME = timedelta(hours=2)


def main(*providers):
    for provider_key in providers:
        print "Cleaning up", provider_key
        api = get_mgmt(provider_key).capi
        try:
            volumes = api.volumes.findall(attachments=[])
        except Exception as e:
            print "Connect to provider failed:", provider_key, type(e).__name__, str(e)
            continue

        for volume in volumes:
            if iso8601.parse_date(volume.created_at) < (datetime.now(tz=local_tz) - GRACE_TIME):
                print "Deleting", volume.id
                try:
                    volume.delete()
                except Exception as e:
                    print "Delete failed:", type(e).__name__, str(e)


if __name__ == "__main__":
    provs = sys.argv[1:]
    if provs:
        main(*provs)
    else:
        main(*list_providers("openstack"))
