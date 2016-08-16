#!/bin/env python2
from __future__ import unicode_literals
import argparse
import sys

from utils.appliance import IPAppliance


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('hostname', nargs='?', default=None,
        help='hostname or ip address of target appliance')
    parser.add_argument('start', action="store_true", default=False, help='Start Merkyl?')
    args = parser.parse_args()

    if args.hostname is not None:
        ip_a = IPAppliance(args.hostname)
    else:
        ip_a = IPAppliance.from_url()

    ip_a.deploy_merkyl(args.start)


if __name__ == '__main__':
    sys.exit(main())
