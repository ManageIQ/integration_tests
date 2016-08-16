#!/usr/bin/env python2

"""Wait for an appliance UI to be usable

Specifically, it will block until the specified URL returns status code 200.

It will use base_url from conf.env by default.

"""
from __future__ import unicode_literals
import argparse
import sys

from utils.appliance import IPAppliance


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('url', nargs='?', default=None,
        help='URL of target appliance, e.g. "https://ip_or_host/"')
    parser.add_argument('--num-sec', default=600, type=int, dest='num_sec',
        help='Maximum number of seconds to wait before giving up, default 600 (10 minutes)')

    args = parser.parse_args()
    if args.url:
        ip_a = IPAppliance.from_url(args.url)
    else:
        ip_a = IPAppliance()
    result = ip_a.wait_for_web_ui(timeout=args.num_sec)

    if not result:
        return 1


if __name__ == '__main__':
    sys.exit(main())
