#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Cleanup unassigned floating ips

Usage: scripts/cleanup_openstack_fips.py [optional list of provider keys]

If no providers specified, it will cleanup all of them.

"""
import sys
from traceback import format_exc

from utils.providers import list_provider_keys, get_mgmt


def main(*providers):
    for provider_key in list_provider_keys('openstack'):
        print('Checking {}'.format(provider_key))
        api = get_mgmt(provider_key).api
        try:
            fips = api.floating_ips.findall(fixed_ip=None)
        except Exception:
            print('Unable to get fips for {}:'.format(provider_key))
            print(format_exc().splitlines()[-1])
            continue

        for fip in fips:
            print('Deleting {} on {}'.format(fip.ip, provider_key))
            fip.delete()
            print('{} deleted'.format(fip.ip))


if __name__ == "__main__":
    provs = sys.argv[1:]
    if provs:
        main(*provs)
    else:
        main(*list_provider_keys("openstack"))
