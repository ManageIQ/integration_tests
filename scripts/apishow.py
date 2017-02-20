#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This script browses through the REST API and shows all collections,
subcollections and their actions.
Optionally it can add coverage info taken from cfme log file to each action.
"""
from __future__ import print_function

import argparse
import os
import random
import re
import warnings

from collections import namedtuple
from utils import conf
from utils.path import log_path
from manageiq_client.api import ManageIQClient as MiqApi


Coverage = namedtuple('Coverage', 'method, action, collection, entity, subcollection, subentity')


def _init_store(key, store):
    """Create key with empty dictionary if key is not already present."""

    if key not in store:
        store[key] = {}


def parse_coverage_line(line):
    """Parse line with RESTAPI coverage log record."""

    method = action = collection = entity = subcollection = subentity = None

    try:
        method = re.search(r'\[RESTAPI\] ([A-Z]*) http', line).group(1)
    except AttributeError:
        # line not in expected format
        return

    searches = [
        # collection, e.g. /api/vms
        r'/api/([a-z_]*) ',
        # entity, e.g. /api/vms/1
        r'/api/([a-z_]*)/([0-9]*) ',
        # subcollection, e.g. /api/vms/1/tags
        r'/api/([a-z_]*)/([0-9]*)/([a-z_]*) ',
        # subcollection entity, e.g. /api/vms/1/tags/10
        r'/api/([a-z_]*)/([0-9]*)/([a-z_]*)/([0-9]*) '
    ]

    for expr in searches:
        search = re.search(expr, line)
        try:
            collection = search.group(1)
            entity = search.group(2)
            subcollection = search.group(3)
            subentity = search.group(4)
        except (AttributeError, IndexError):
            pass
        if collection:
            break
    else:
        return

    if '[RESTAPI] POST http' in line:
        try:
            action = re.search(r'\'action\': u?\'([a-z_]*)', line).group(1)
        except AttributeError:
            pass

    return Coverage(
        method=method,
        action=action,
        collection=collection,
        entity=entity,
        subcollection=subcollection,
        subentity=subentity)


def save_coverage_record(record, store):
    """Save parsed RESTAPI coverage log record into dictionary."""

    _init_store(record.collection, store)
    current = store[record.collection]

    if record.subcollection:
        _init_store(record.subcollection, current)
        current = current[record.subcollection]

    _init_store('entity', current)

    if record.subentity:
        target = current['entity']
    elif record.subcollection:
        target = current
    elif record.entity:
        target = current['entity']
    else:
        target = current

    if 'methods' not in target:
        target['methods'] = set([record.method])
    else:
        target['methods'].add(record.method)

    if record.action:
        if 'actions' not in target:
            target['actions'] = set([record.action])
        else:
            target['actions'].add(record.action)


def get_coverage(logfile, store):
    """Read pytest log file and look for RESTAPI coverage log records."""

    with open(logfile, 'r') as infile:
        for line in infile:
            if '[RESTAPI]' not in line or 'http' not in line:
                continue

            record = parse_coverage_line(line)
            if not record:
                continue

            save_coverage_record(record, store)


def get_collections_info(api, store):
    """Get info about collections, subcollections and their actions."""

    try:
        subcollections = api.collections.users[0].SUBCOLLECTIONS
    except IndexError:
        subcollections = {}

    def _process_collection(collection, store):
        _init_store(collection.name, store)

        try:
            actions = collection.action.all
        except KeyError:
            actions = []

        if 'actions_avail' not in store[collection.name]:
            store[collection.name]['actions_avail'] = set(actions)

        try:
            collection_len = len(collection)
        except AttributeError:
            collection_len = 0

        if collection_len > 0:
            _init_store('entity', store[collection.name])
            entity = random.choice(collection)

            try:
                actions = entity.action.all
            except KeyError:
                actions = []
            if 'actions_avail' not in store[collection.name]['entity']:
                store[collection.name]['entity']['actions_avail'] = set(actions)

            if collection.name in subcollections:
                for subcol_name in subcollections[collection.name]:
                    try:
                        subcol = getattr(entity, subcol_name)
                    except AttributeError:
                        continue
                    _process_collection(subcol, store[collection.name])

    for collection in api.collections.all:
        _process_collection(collection, store)


def print_info(store):
    """Print info about collections together with coverage info when available."""

    for name, collection in sorted(store.iteritems()):
        print('=' * (2 + len(name)))
        print('* {}'.format(name))

        def _print_resource(res_title, res_dict):
            if 'actions_avail' in res_dict and res_dict['actions_avail']:
                print('  {} actions:'.format(res_title))
                covered = True if 'actions' in res_dict else False
                for action in res_dict['actions_avail']:
                    print('    * {}{}'.format(
                        action,
                        ' OK' if covered and action in res_dict['actions'] else ''))
            if 'entity' in res_dict:
                _print_resource('{} entity'.format(res_title), res_dict['entity'])

            for key, subcollection in sorted(res_dict.iteritems()):
                if key in ('actions', 'actions_avail', 'entity', 'methods'):
                    continue
                _print_resource('Subcollection "{}"'.format(key), subcollection)

        _print_resource('Collection', collection)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--address',
        default=conf.env.get('base_url', None),
        help="hostname or ip address of target appliance, "
             "default pulled from local environment conf")
    parser.add_argument(
        '--logfile',
        metavar='FILE',
        default=os.path.join(log_path.strpath, 'cfme.log'),
        help="path to cfme log file, default: %(default)s")
    args = parser.parse_args()

    # we are really not interested in any warnings and "warnings.simplefilter('ignore')"
    # doesn't work when it's redefined later in the REST API client
    warnings.showwarning = lambda *args, **kwargs: None

    api = MiqApi(
        '{}/api'.format(args.address.rstrip('/')),
        (conf.credentials['default']['username'], conf.credentials['default']['password']),
        verify_ssl=False)

    print("Appliance IP: {}".format(args.address))

    store = {}

    get_collections_info(api, store)

    if os.path.isfile(args.logfile):
        get_coverage(args.logfile, store)

    print_info(store)
