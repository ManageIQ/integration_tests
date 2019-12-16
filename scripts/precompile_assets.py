#!/usr/bin/env python3
"""SSH into a running appliance and compile ui assets.
"""
import argparse
import sys

from cfme.utils.appliance import DefaultAppliance


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', nargs='?', default=None,
        help='hostname or ip address of target appliance')

    args = parser.parse_args()
    ip_a = DefaultAppliance(hostname=args.address)

    status = ip_a.precompile_assets()
    if status == 0:
        ip_a.evmserverd.restart()
        print("EVM service restarted, UI should be available shortly")
    return status


if __name__ == '__main__':
    sys.exit(main())
