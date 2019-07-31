#!/usr/bin/env python3
"""SSH into a running appliance and loosen postgres connections"""
import argparse
import sys

from cfme.utils.appliance import IPAppliance


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', help='hostname or ip address of target appliance',
        nargs='?', default=None)
    parser.add_argument('--with_ssl', help='update for ssl connections', action="store_true")

    args = parser.parse_args()
    ip_a = IPAppliance(hostname=args.address)
    return ip_a.loosen_pgssl()


if __name__ == '__main__':
    sys.exit(main())
