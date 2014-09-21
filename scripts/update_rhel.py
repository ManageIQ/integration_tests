#!/usr/bin/env python2

"""Run yum updates against a given repo
"""

import argparse
import sys
from utils.appliance import IPAppliance


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', help='hostname or ip address of target appliance')
    parser.add_argument("-u", "--url", help="url(s) to use for update",
        dest="urls", action="append")
    parser.add_argument('--reboot', help='reboot after installation ' +
        '(required for proper operation)', action="store_true")

    args = parser.parse_args()

    ip_a = IPAppliance(args.address)
    status, out = ip_a.update_rhel(*args.urls)

    if status == 0:
        print out
        print 'Appliance update complete'
        if args.reboot:
            ip_a.reboot()

    return status


if __name__ == '__main__':
    sys.exit(main())
