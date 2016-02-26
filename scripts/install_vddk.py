#!/usr/bin/env python2

"""SSH into a running appliance and install VMware VDDK.
"""

import argparse
import sys
from urlparse import urlparse
from utils.appliance import IPAppliance
from utils.conf import env


def log(message):
    print("[VDDK-INSTALL] {}".format(message))


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--address',
        help='hostname or ip address of target appliance', default=env.get("base_url", None))
    parser.add_argument('--vddk_url', help='url to download vddk pkg')
    parser.add_argument('--reboot', help='reboot after installation ' +
                        '(required for proper operation)', action="store_true")
    parser.add_argument('--force',
                        help='force installation if version detected', action="store_true")

    args = parser.parse_args()

    address = urlparse(args.address).netloc

    appliance = IPAppliance(address=address)
    appliance.install_vddk(
        reboot=args.reboot, force=args.force, vddk_url=args.vddk_url, log_callback=log)


if __name__ == '__main__':
    sys.exit(main())
