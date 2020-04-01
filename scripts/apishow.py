#!/usr/bin/env python3
"""
This script browses through the REST API and shows all collections,
subcollections and their actions.
Optionally it can add coverage info taken from cfme log file to each action.
"""
import argparse
import os
import random
import re
import warnings
from collections import namedtuple

from manageiq_client.api import ManageIQClient as MiqApi

from cfme.utils import conf
from cfme.utils.appliance import get_or_create_current_appliance
from cfme.utils.path import log_path


Coverage = namedtuple('Coverage', 'method, action, collection, entity, subcollection, subentity')

method_re = re.compile(r'\[RESTAPI\] ([A-Z]*) http')
action_re = re.compile(r'\'action\': u?\'([a-z_]*)')
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
searches_re = [re.compile(search) for search in searches]


def _init_store(key, store):
    """Create key with empty dictionary if key is not already present."""

    if key not in store:
        store[key] = {}


def parse_coverage_line(line):
    """Parse line with RESTAPI coverage log record."""

    method = action = collection = entity = subcollection = subentity = None

    try:
        method = method_re.search(line).group(1)
    except AttributeError:
        # line not in expected format
        return

    if method not in ('POST', 'DELETE'):
        return

    try:
        action = action_re.search(line).group(1)
    except AttributeError:
        # line not in expected format
        return

    for expr in searches_re:
        search = expr.search(line)
        try:
            collection = search.group(1)
            entity = search.group(2)
            subcollection = search.group(3)
            subentity = search.group(4)
        except (AttributeError, IndexError):
            pass
        if collection:
            # found matching expression
            break
    else:
        return

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

    _init_store('actions', target)
    if record.action in target['actions']:
        if record.method not in target['actions'][record.action]:
            target['actions'][record.action].append(record.method)
    else:
        target['actions'][record.action] = [record.method]


def get_coverage(logfile, store):
    """Read pytest log file and look for RESTAPI coverage log records."""

    with open(logfile) as infile:
        for line in infile:
            if '[RESTAPI]' not in line or 'http' not in line:
                continue

            record = parse_coverage_line(line)
            if not record:
                continue

            save_coverage_record(record, store)


def get_collections_info(api, store):
    """Get info about collections, subcollections and their actions."""

    def _get_actions(entity, store):
        try:
            entity.reload_if_needed()
        except KeyError:
            return
        try:
            actions = entity._actions
        except AttributeError:
            return
        for record in actions:
            if record['name'] in store:
                store[record['name']].append(record['method'].upper())
            else:
                store[record['name']] = [record['method'].upper()]

    def _process_collection(collection, store, is_subcol=False):
        _init_store(collection.name, store)
        _init_store('actions_avail', store[collection.name])
        _get_actions(collection, store[collection.name]['actions_avail'])

        try:
            collection_len = len(collection)
        except AttributeError:
            return
        if collection_len <= 0:
            return

        _init_store('entity', store[collection.name])
        _init_store('actions_avail', store[collection.name]['entity'])
        entity = random.choice(collection)
        _get_actions(entity, store[collection.name]['entity']['actions_avail'])

        # don't try to process subcollections if we are already in subcollection
        if not is_subcol:
            subcollections = collection.options().get('subcollections', [])
            for subcol_name in subcollections:
                try:
                    subcol = getattr(entity, subcol_name)
                except AttributeError:
                    continue
                _process_collection(subcol, store[collection.name], is_subcol=True)

    for collection in api.collections.all:
        _process_collection(collection, store)


def print_info(store):
    """Print info about collections together with coverage info when available."""

    for name, collection in sorted(store.items()):
        print('=' * (2 + len(name)))
        print(f'* {name}')

        def _print_resource(res_title, res_dict):
            if 'actions_avail' in res_dict and res_dict['actions_avail']:
                print(f'  {res_title} actions:')
                covered = True if 'actions' in res_dict else False
                for action, methods in res_dict['actions_avail'].items():
                    methods_num = len(methods)
                    only_post = True if methods_num == 1 and methods[0] == 'POST' else False
                    if (covered and only_post and
                            action in res_dict['actions'] and
                            'POST' in res_dict['actions'][action]):
                        cov_str = ' OK'
                    else:
                        cov_str = ''
                    print(f'    * {action}{cov_str}')
                    # not only POST method exists for this action, list them all
                    if not only_post:
                        for method in methods:
                            print('        {}{}'.format(
                                method,
                                ' OK' if covered and method in res_dict['actions'][action] else ''))
            if 'entity' in res_dict:
                _print_resource(f'{res_title} entity', res_dict['entity'])

            for key, subcollection in sorted(res_dict.items()):
                if key in ('actions', 'actions_avail', 'entity'):
                    continue
                _print_resource(f'Subcollection "{key}"', subcollection)

        _print_resource('Collection', collection)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--url',
        default=None,
        help="URL of the target appliance, default pulled from local environment conf")
    parser.add_argument(
        '--logfile',
        metavar='FILE',
        default=os.path.join(log_path.strpath, 'cfme.log'),
        help="path to cfme log file, default: %(default)s")
    args = parser.parse_args()

    appliance_url = args.url or get_or_create_current_appliance().url

    # we are really not interested in any warnings and "warnings.simplefilter('ignore')"
    # doesn't work when it's redefined later in the REST API client
    warnings.showwarning = lambda *args, **kwargs: None

    api = MiqApi(
        '{}/api'.format(appliance_url.rstrip('/')),
        (conf.credentials['default']['username'], conf.credentials['default']['password']),
        verify_ssl=False)

    print(f"Appliance URL: {appliance_url}")

    store = {}

    get_collections_info(api, store)

    if os.path.isfile(args.logfile):
        get_coverage(args.logfile, store)

    print_info(store)
