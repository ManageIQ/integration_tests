#!/usr/bin/env python2
"""
Given a provider from cfme_data along with a vm_name,
how long you want the vm to run (uptime, in seconds),
and how long you want the vm to be off (downtime, in seconds)
this script will toggle the vm on and off.

Example usage:

scripts/toggle_vm.py provider_name vm_name  uptime downtime

"""

import argparse
import sys
import time

from utils.providers import get_mgmt


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('provider_name',
        help='provider name in cfme_data')
    parser.add_argument('vm_name', help='the name of the VM on which to act')
    parser.add_argument('uptime', type=int,
        help='how long do you want the vm to be on (in seconds)')
    parser.add_argument('downtime', type=int,
        help='how long do you want the vm to be off (in seconds)')

    args = parser.parse_args()

    # Make sure the VM is off to start
    provider = get_mgmt(args.provider_name)

    if provider.is_vm_running(args.vm_name):
        provider.stop_vm(args.vm_name)
        provider.vm_status(args.vm_name)

    # Toggle the VM On and Off based on the Uptime and Downtime input arguments
    # The script diconnects from the provider before each sleep and reconnects after
    # each sleep to prevent it from timing out
    while True:
        try:
            # Initialize start_success to False so it enters the first while loop
            # and the times_failed_counter to 0
            start_success = False
            times_failed_counter = 0
            # Turn the VM on for the specified amount of time
            # If it can't find the VM, keep trying for 30 minutes
            while not start_success:
                try:
                    provider.start_vm(args.vm_name)
                    provider.vm_status(args.vm_name)
                    start_success = True
                    provider.disconnect()
                    time.sleep(args.uptime)
                    provider = get_mgmt(args.provider_name)
                except Exception:
                    time.sleep(60)
                    times_failed_counter += 1
                    if(times_failed_counter == 30):
                        raise

            # Initialize stop_success to False so it enters the first while loop
            # and the times_failed_counter to 0
            stop_success = False
            times_failed_counter = 0
            # Turn the VM off for the specified amount of time
            # If it can't find the VM, keep trying for 30 minutes
            while not stop_success:
                try:
                    provider.stop_vm(args.vm_name)
                    provider.vm_status(args.vm_name)
                    stop_success = True
                    provider.disconnect()
                    time.sleep(args.downtime)
                    provider = get_mgmt(args.provider_name)
                except Exception:
                    time.sleep(60)
                    times_failed_counter += 1
                    if(times_failed_counter == 30):
                        raise
        except(KeyboardInterrupt):
            return 0


if __name__ == '__main__':
    sys.exit(main())
