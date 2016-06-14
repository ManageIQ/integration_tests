#!/usr/bin/env python2

"""SSH into a running appliance and compile ui assets.
"""

import argparse
import sys

from utils.appliance import IPAppliance


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address', nargs='?', default=None,
        help='hostname or ip address of target appliance')

    args = parser.parse_args()
    ip_a = IPAppliance(args.address)

    status = ip_a.precompile_assets()
    if status == 0:
        ip_a.restart_evm_service()
        print("EVM service restarted, UI should be available shortly")
    return status

if __name__ == '__main__':
    sys.exit(main())
