#!/usr/bin/env python2

"""Add/activate/remove a direct_lun disk on a rhevm appliance
"""

import argparse
import sys
from utils.providers import get_mgmt


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--provider', dest='provider_name', help='provider name in cfme_data')
    parser.add_argument('--vm_name', help='the name of the VM on which to act')
    parser.add_argument('--remove', help='remove disk from vm', action="store_true")
    args = parser.parse_args()

    provider = get_mgmt(args.provider_name)

    provider.connect_direct_lun_to_appliance(args.vm_name, args.remove)


if __name__ == '__main__':
    sys.exit(main())
