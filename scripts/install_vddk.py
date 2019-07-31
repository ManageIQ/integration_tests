#!/usr/bin/env python3
"""SSH into a running appliance and install VMware VDDK.
"""
import argparse
import sys

from six.moves.urllib.parse import urlparse

from cfme.utils.appliance import get_or_create_current_appliance
from cfme.utils.appliance import IPAppliance


def log(message):
    print("[VDDK-INSTALL] {}".format(message))


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--address',
        help='hostname or ip address of target appliance', default=None)
    parser.add_argument('--vddk_url', help='url to download vddk pkg')
    parser.add_argument('--reboot', help='reboot after installation ' +
                        '(required for proper operation)', action="store_true")
    parser.add_argument('--force',
                        help='force installation if version detected', action="store_true")

    args = parser.parse_args()

    if not args.address:
        appliance = get_or_create_current_appliance()
    else:
        appliance = IPAppliance(hostname=urlparse(args.address).netloc)

    appliance.install_vddk(
        reboot=args.reboot, force=args.force, vddk_url=args.vddk_url, log_callback=log)


if __name__ == '__main__':
    sys.exit(main())
