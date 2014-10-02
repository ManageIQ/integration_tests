#!/usr/bin/env python2

"""Patch appliance.js on a running appliance with an ajax wait fix

The 'patch' utility must be installed for this script to work.

This should only be needed on appliances before version 5.2.2.

"""

import argparse
import sys

from utils.appliance import IPAppliance


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', nargs='?', default=None,
        help='hostname or ip address of target appliance')
    parser.add_argument('-R', '--reverse', help='flag to indicate the patch should be undone',
        action='store_true', default=False, dest='reverse')

    args = parser.parse_args()
    return IPAppliance(args.address).patch_ajax_wait(args.reverse)


if __name__ == '__main__':
    sys.exit(main())
