#!/usr/bin/env python

"""Wait for an appliance UI to be usable

Specifically, it will block until the specified URL returns status code 200.

It will use base_url from conf.env by default.

"""
import argparse
import sys

import requests

from utils.conf import env
from utils.log import logger
from utils.wait import wait_for, TimedOutError


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('url', nargs='?', default=env['base_url'],
        help='URL of target appliance, e.g. "https://ip_or_host/"')
    parser.add_argument('--num-sec', default=600, type=int, dest='num_sec',
        help='Maximum number of seconds to wait before giving up, default 600 (10 minutes)')

    args = parser.parse_args()

    def check_appliance_ui(url):
        # Get the URL, don't verify ssl cert
        try:
            response = requests.get(url, timeout=10, verify=False)
            if response.status_code == 200:
                logger.info("Appliance online")
                return True
            else:
                logger.debug('Appliance online, status code %d' %
                    response.status_code)
        except requests.exceptions.Timeout:
            logger.debug('Appliance offline, connection timed out')
        except ValueError:
            # requests exposes invalid URLs as ValueErrors, which is excellent.
            raise
        except Exception as ex:
            logger.debug('Appliance online, but connection failed: %s' % ex.message)
        return False

    try:
        wait_for(check_appliance_ui, [args.url], num_sec=args.num_sec, delay=10)
        return 0
    except TimedOutError:
        return 1

if __name__ == '__main__':
    sys.exit(main())
