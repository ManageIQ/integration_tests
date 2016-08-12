#!/usr/bin/env python2

"""Run yum updates against a given repo
"""

from __future__ import unicode_literals
import argparse
import sys
from utils.appliance import IPAppliance


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', help='hostname or ip address of target appliance')
    parser.add_argument("-u", "--url", help="url(s) to use for update",
        dest="urls", action="append")
    parser.add_argument("-c", "--cleanup", help="Whether to cleanup /etc/yum.repos.d before start",
        dest="cleanup", action="store_true")
    parser.add_argument("--no_wait_ui", help="Whether to NOT wait for UI after reboot",
        dest="no_wait_ui", action="store_false")
    parser.add_argument('--reboot', help='reboot after installation ' +
        '(required for proper operation)', action="store_true", default=False)

    args = parser.parse_args()
    ip_a = IPAppliance(args.address)
    # Don't reboot here, so we can print updates to the console when we do
    res = ip_a.update_rhel(*args.urls, reboot=False, streaming=True, cleanup=args.cleanup)

    if res.rc == 0:
        if args.reboot:
            print('Rebooting')
            ip_a.reboot(wait_for_web_ui=args.no_wait_ui)
        print('Appliance update complete')

    return res.rc


if __name__ == '__main__':
    sys.exit(main())
