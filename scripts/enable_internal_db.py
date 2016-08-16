#!/usr/bin/env python2

"""SSH in to a running appliance and set up an internal DB.

An optional region can be specified (default 0), and the script
will use the first available unpartitioned disk as the data volume
for postgresql.

Running this script against an already configured appliance is
unsupported, hilarity may ensue.

"""

from __future__ import unicode_literals
import argparse
import sys

from utils.appliance import IPAppliance


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('address',
        help='hostname or ip address of target appliance')
    parser.add_argument('--region', default=0, type=int,
        help='region to assign to the new DB')
    args = parser.parse_args()

    print('Initializing Appliance Internal DB')
    ip_a = IPAppliance(args.address)
    status, out = ip_a.enable_internal_db(args.region)

    if status != 0:
        print('Enabling DB failed with error:')
        print(out)
        sys.exit(1)
    else:
        print('DB Enabled, evm watchdog should start the UI shortly.')


if __name__ == '__main__':
    sys.exit(main())
