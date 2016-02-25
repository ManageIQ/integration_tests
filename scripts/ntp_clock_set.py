#!/usr/bin/env python2
# -*- coding: utf-8 -*-

""" Set correct time via NTP

This script prevents failing of the tests with sudden time update from NTP.
It forces an immediate update of the time bringing it to the correct one.
Therefore the "Session timeout" error cannot happen when the CFME watchdog's ntp update comes.
Requires this in conf/cfme_data.yaml

clock_servers:
- server1.org
- server2.org
...
- serverN.org
"""

import argparse

from utils.appliance import IPAppliance


def main():
    parser = argparse.ArgumentParser(
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('address', nargs="?", default=None,
        help='hostname or ip address of target appliance')
    args = parser.parse_args()
    ip_a = IPAppliance(args.address)
    ip_a.fix_ntp_clock()
    print("Time was set")


if __name__ == "__main__":
    exit(main())
