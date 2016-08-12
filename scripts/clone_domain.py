#!/usr/bin/env python2

"""Clone an Automate Domain

eg, clone_domain.py xx.xx.xx.xx ManageIQ Default

This can take several minutes to run.

"""
from __future__ import unicode_literals
import argparse
import sys

from utils.appliance import IPAppliance


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('hostname', nargs='?', default=None,
        help='hostname or ip address of target appliance')
    parser.add_argument('source', nargs='?', default='ManageIQ',
        help='Source Domain name')
    parser.add_argument('dest', nargs='?', default='Default',
        help='Destination Domain name')
    args = parser.parse_args()

    ip_a = IPAppliance(args.hostname)
    status, out = ip_a.clone_domain(args.source, args.dest)
    return status


if __name__ == '__main__':
    sys.exit(main())
