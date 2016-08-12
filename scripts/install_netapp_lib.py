#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""SSH into a running appliance and install Netapp SDK
"""

from __future__ import unicode_literals
import argparse
from urlparse import urlparse
from utils.appliance import IPAppliance
from utils.conf import cfme_data, env


def parse_if_not_none(o):
    if o is None:
        return None
    url = urlparse(o)
    return url.netloc or url.path  # If you pass a plain IP, it will get in the .path


def log(s):
    print(s)


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--address',
        help='hostname or ip address of target appliance',
        default=parse_if_not_none(env.get("base_url", None)))
    parser.add_argument(
        '--sdk_url',
        help='url to download sdk pkg',
        default=cfme_data.get("basic_info", {}).get("netapp_sdk_url", None))
    parser.add_argument('--restart', help='restart evmserverd after installation ' +
        '(required for proper operation)', action="store_true")

    args = parser.parse_args()
    print('Address: {}'.format(args.address))
    print('SDK URL: {}'.format(args.sdk_url))
    print('Restart: {}'.format(args.restart))

    appliance = IPAppliance(address=args.address)
    appliance.install_netapp_sdk(sdk_url=args.sdk_url, reboot=args.restart, log_callback=log)


if __name__ == '__main__':
    main()
