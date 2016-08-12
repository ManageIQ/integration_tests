#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""This script browses thorugh the REST API and shows all collections and their actions"""
# TODO: Subcollections
import argparse
import random
import re

from utils import conf
from miqclient.api import API

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument(
    '--address',
    help='hostname or ip address of target appliance', default=conf.env.get("base_url", None))
args = parser.parse_args()


api = API(
    "{}/api".format(
        args.address if not args.address.endswith("/") else re.sub(r"/+$", "", args.address)),
    ("admin", "smartvm"))
print("Appliance IP: {}".format(args.address))

for collection in api.collections.all:
    print("=" * (2 + len(collection.name)))
    print("* {}".format(collection.name))
    actions = collection.action.all
    if actions:
        print("  Collection actions:")
        for action in actions:
            print("    * {}".format(action))
    if len(collection) > 0:
        entity = random.choice(collection)
        actions = entity.action.all
        if actions:
            print("  Entity actions:")
            for action in actions:
                print("    * {}".format(action))
    else:
        print("  No items in the collection to check per-item actions.")
