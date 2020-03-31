#!/usr/bin/env python3
"""Cleanup unassigned floating ips

Usage: scripts/cleanup_openstack_fips.py [optional list of provider keys]

If no providers specified, it will cleanup all of them.

"""
import sys
from traceback import format_exc

from cfme.utils.providers import get_mgmt
from cfme.utils.providers import list_provider_keys


def main(*providers):
    for provider_key in list_provider_keys('openstack'):
        print(f'Checking {provider_key}')
        api = get_mgmt(provider_key).api
        try:
            fips = api.floating_ips.findall(fixed_ip=None)
        except Exception:
            print(f'Unable to get fips for {provider_key}:')
            print(format_exc().splitlines()[-1])
            continue

        for fip in fips:
            print(f'Deleting {fip.ip} on {provider_key}')
            fip.delete()
            print(f'{fip.ip} deleted')


if __name__ == "__main__":
    provs = sys.argv[1:]
    if provs:
        main(*provs)
    else:
        main(*list_provider_keys("openstack"))
