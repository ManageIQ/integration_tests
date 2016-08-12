#!/usr/bin/env python2
"""SSH into a running appliance and loosen postgres connections"""
from __future__ import unicode_literals
import argparse
import sys

from utils.appliance import IPAppliance


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', help='hostname or ip address of target appliance',
        nargs='?', default=None)
    parser.add_argument('--with_ssl', help='update for ssl connections', action="store_true")

    args = parser.parse_args()
    ip_a = IPAppliance(args.address)
    return ip_a.loosen_pgssl()


if __name__ == '__main__':
    sys.exit(main())
