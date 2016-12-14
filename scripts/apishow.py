#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""This script browses thorugh the REST API and shows all collections and their actions"""
# TODO: Subcollections
import argparse
import random
import re
import warnings

from utils import conf
from manageiq_client.api import ManageIQClient as MiqApi

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument(
    '--address',
    help='hostname or ip address of target appliance', default=conf.env.get("base_url", None))
args = parser.parse_args()


warnings.simplefilter('ignore')
api = MiqApi(
    "{}/api".format(
        args.address if not args.address.endswith("/") else re.sub(r"/+$", "", args.address)),
    ("admin", "smartvm"),
    verify_ssl=False)
print("Appliance IP: {}".format(args.address))

for collection in api.collections.all:
    print("=" * (2 + len(collection.name)))
    print("* {}".format(collection.name))
    try:
        actions = collection.action.all
    except KeyError:
        actions = None

    if actions:
        print("  Collection actions:")
        for action in actions:
            print("    * {}".format(action))

    try:
        collection_len = len(collection)
    except AttributeError:
        collection_len = 0

    if collection_len > 0:
        entity = random.choice(collection)
        actions = entity.action.all
        if actions:
            print("  Entity actions:")
            for action in actions:
                print("    * {}".format(action))
    else:
        print("  No items in the collection to check per-item actions.")
