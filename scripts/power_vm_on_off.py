#!/usr/bin/env python
"""
Given a provider from cfme_data along with a vm_name, and whether
you want to turn the vm on or off
this script will toggle the vm on or off

Example usage:

scripts/power_vm_on.py provider_name vm_name on (or off)

"""

import argparse
import sys


from utils.providers import provider_factory


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('provider_name',
        help='provider name in cfme_data')
    parser.add_argument('vm_name', help='the name of the VM on which to act')
    parser.add_argument('on_or_off', help='do you want to turn the vm on or off')

    args = parser.parse_args()

    provider = provider_factory(args.provider_name)

    if args.on_or_off == 'on':
        if provider.is_vm_stopped(args.vm_name):
            provider.start_vm(args.vm_name)
            provider.vm_status(args.vm_name)
    if args.on_or_off == 'off':
        if provider.is_vm_running(args.vm_name):
            provider.stop_vm(args.vm_name)
            provider.vm_status(args.vm_name)

if __name__ == '__main__':
    sys.exit(main())
