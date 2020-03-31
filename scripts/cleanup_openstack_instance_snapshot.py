#!/usr/bin/env python3
"""Cleanup unused instance snapshot from glance repository

Usage: scripts/cleanup_openstack_instance_snapshot.py [optional list of provider keys]

If no providers specified, it will cleanup all of them.

"""
import argparse
from datetime import datetime
from datetime import timedelta

import tzlocal

from cfme.utils.log import add_stdout_handler
from cfme.utils.log import logger
from cfme.utils.providers import get_mgmt
from cfme.utils.providers import list_provider_keys

LOCAL_TZ = tzlocal.get_localzone()
GRACE_TIME = timedelta(hours=2)
TIME_LIMIT = datetime.now(tz=LOCAL_TZ) - GRACE_TIME

# log to stdout too
add_stdout_handler(logger)


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--name', default='test_snapshot_',
                        help='Starting pettern of snaphsot name '
                             'e.g. --name test_ delete all snapshot starting with test_')
    parser.add_argument('--providers', default=list_provider_keys("openstack"), nargs='+',
                        help='List of provider keys e.g. --providers rhos13 rhos12'
                        )
    args = parser.parse_args()
    return args


def main(args):
    """ Cleanup all snapshots name starting with test_snapshot and created by >= 2 hours before

    :param providers: Lists provider keys
    :return:
    """
    for provider_key in args.providers:
        logger.info(f"Cleaning up {provider_key}")
        provider_obj = get_mgmt(provider_key)

        try:
            images = provider_obj.list_templates()
        except Exception:
            logger.exception("Unable to get the list of templates")
            continue

        for img in images:
            if img.name.startswith(args.name) and img.creation_time < TIME_LIMIT:
                logger.info(f"Deleting {img.name}")
                try:
                    img.delete()
                except Exception:
                    logger.exception(f"Snapshot {img.name} Deletion failed")


if __name__ == "__main__":
    main(parse_cmd_line())
