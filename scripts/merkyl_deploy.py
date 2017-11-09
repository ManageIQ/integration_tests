#!/bin/env python2
import argparse
import sys

from cfme.utils.appliance import IPAppliance


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('hostname', help='hostname or ip address of target appliance')
    parser.add_argument('start', action="store_true", default=False, help='Start Merkyl?')
    args = parser.parse_args()

    ip_a = IPAppliance(hostname=args.hostname)

    ip_a.deploy_merkyl(args.start)


if __name__ == '__main__':
    sys.exit(main())
