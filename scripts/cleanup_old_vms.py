#!/usr/bin/env python2

import argparse
import datetime
import re
import sys
from collections import defaultdict
from threading import Lock, Thread

from utils.log import logger
from utils.providers import list_all_providers, get_mgmt

lock = Lock()


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('-f', '--force', default=True, action='store_false', dest='prompt',
        help='Do not prompt before deleting VMs (danger zone!)')
    parser.add_argument('--max-hours', default=24,
        help='Max hours since the VM was created or last powered on '
        '(varies by provider, default 24)')
    parser.add_argument('--provider', dest='providers', action='append', default=None,
        help='Provider(s) to inspect, can be used multiple times', metavar='PROVIDER')
    parser.add_argument('text_to_match', nargs='*', default=['^test_', '^jenkins', '^i-'],
        help='Regex in the name of vm to be affected, can be use multiple times'
        ' (Defaults to "^test_" and "^jenkins")')
    args = parser.parse_args()
    return args


def match(matchers, vm_name):
    for matcher in matchers:
        if matcher.match(vm_name):
            return True
    else:
        return False


def process_provider_vms(provider_key, matchers, delta, vms_to_delete):
    with lock:
        print('{} processing'.format(provider_key))
    try:
        now = datetime.datetime.now()
        with lock:
            # Known conf issue :)
            provider = get_mgmt(provider_key)
        for vm_name in provider.list_vm():
            if not match(matchers, vm_name):
                continue

            try:
                vm_creation_time = provider.vm_creation_time(vm_name)
            except:
                logger.error('Failed to get creation/boot time for {} on {}'.format(
                    vm_name, provider_key))
                continue

            if vm_creation_time + delta < now:
                vm_delta = now - vm_creation_time
                with lock:
                    vms_to_delete[provider_key].add((vm_name, vm_delta))
        with lock:
            print('{} finished'.format(provider_key))
    except Exception as ex:
        with lock:
            # Print out the error message too because logs in the job get deleted
            print('{} failed ({}: {})'.format(provider_key, type(ex).__name__, str(ex)))
        logger.error('failed to process vms from provider {}'.format(provider_key))
        logger.exception(ex)


def delete_provider_vms(provider_key, vm_names):
    with lock:
        print('Deleting VMs from {} ...'.format(provider_key))

    try:
        with lock:
            provider = get_mgmt(provider_key)
    except Exception as e:
        with lock:
            print("Could not retrieve the provider {}'s mgmt system ({}: {})".format(
                provider_key, type(e).__name__, str(e)))
            logger.exception(e)

    for vm_name in vm_names:
        with lock:
            print("Deleting {} from {}".format(vm_name, provider_key))
        try:
            provider.delete_vm(vm_name)
        except Exception as e:
            with lock:
                print('Failed to delete {} on {}'.format(vm_name, provider_key))
                logger.exception(e)
    with lock:
        print("{} is done!".format(provider_key))


def cleanup_vms(texts, max_hours=24, providers=None, prompt=True):
    providers = providers or list_all_providers()
    delta = datetime.timedelta(hours=int(max_hours))
    vms_to_delete = defaultdict(set)
    thread_queue = []
    # precompile regexes
    matchers = [re.compile(text) for text in texts]

    for provider_key in providers:
        thread = Thread(target=process_provider_vms,
            args=(provider_key, matchers, delta, vms_to_delete))
        # Mark as daemon thread for easy-mode KeyboardInterrupt handling
        thread.daemon = True
        thread_queue.append(thread)
        thread.start()

    # Join the queued calls
    for thread in thread_queue:
        thread.join()

    for provider_key, vm_set in vms_to_delete.items():
        print('{}:'.format(provider_key))
        for vm_name, vm_delta in vm_set:
            days, hours = vm_delta.days, vm_delta.seconds / 3600
            print(' {} is {} days, {} hours old'.format(vm_name, days, hours))

    if vms_to_delete and prompt:
        yesno = raw_input('Delete these VMs? [y/N]: ')
        if str(yesno).lower() != 'y':
            print('Exiting.')
            return 0

    if not vms_to_delete:
        print('No VMs to delete.')

    thread_queue = []
    for provider_key, vm_set in vms_to_delete.items():
        thread = Thread(target=delete_provider_vms,
            args=(provider_key, [name for name, t_delta in vm_set]))
        # Mark as daemon thread for easy-mode KeyboardInterrupt handling
        thread.daemon = True
        thread_queue.append(thread)
        thread.start()

    for thread in thread_queue:
        thread.join()

    print("Deleting finished")

if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(cleanup_vms(args.text_to_match, args.max_hours, args.providers, args.prompt))
