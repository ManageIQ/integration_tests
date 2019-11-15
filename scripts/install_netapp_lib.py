#!/usr/bin/env python3
"""SSH into a running appliance and install Netapp SDK
"""
import argparse

from cfme.utils.appliance import get_or_create_current_appliance
from cfme.utils.appliance import IPAppliance
from cfme.utils.conf import cfme_data


def log(s):
    print(s)


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--address',
        help='hostname or ip address of target appliance',
        default=None)
    parser.add_argument(
        '--sdk_url',
        help='url to download sdk pkg',
        default=cfme_data.get("basic_info", {}).get("netapp_sdk_url"))
    parser.add_argument('--restart', help='restart evmserverd after installation ' +
        '(required for proper operation)', action="store_true")

    args = parser.parse_args()
    if not args.address:
        appliance = get_or_create_current_appliance()
    else:
        appliance = IPAppliance(hostname=args.address)
    print('Address: {}'.format(appliance.hostname))
    print('SDK URL: {}'.format(args.sdk_url))
    print('Restart: {}'.format(args.restart))

    appliance.install_netapp_sdk(sdk_url=args.sdk_url, reboot=args.restart, log_callback=log)


if __name__ == '__main__':
    main()
