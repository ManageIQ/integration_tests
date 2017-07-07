#!/usr/bin/env python2
import argparse
import datetime
import re
import sys
from collections import namedtuple
from operator import attrgetter
from multiprocessing import Process, Queue

import pytz
from tabulate import tabulate

from utils import net
from utils.log import logger
from utils.conf import cfme_data
from utils.path import log_path
from utils.providers import list_provider_keys, get_mgmt

# Constant strings for the report
PASS = 'PASS'
FAIL = 'FAIL'
NULL = '--'

VmData = namedtuple('VmData', 'provider_key, name, age')
VmReport = namedtuple('VmReport', 'provider_key, name, age, status, result')


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('-f', '--force', default=True, action='store_false', dest='prompt',
                        help='Do not prompt before deleting VMs (danger zone!)')
    parser.add_argument('--max-hours', default=24,
                        help='Max hours since the VM was created or last powered on '
                             '(varies by provider, default 24)')
    parser.add_argument('--provider', dest='providers', action='append', default=None,
                        help='Provider(s) to inspect, can be used multiple times',
                        metavar='PROVIDER')
    parser.add_argument('--outfile', dest='outfile',
                        default=log_path.join('cleanup_old_vms.log').strpath,
                        help='outfile to list ')
    parser.add_argument('text_to_match', nargs='*', default=['^test_', '^jenkins', '^i-'],
                        help='Regex in the name of vm to be affected, can be use multiple times'
                             ' (Defaults to \'^test_\' and \'^jenkins\')')

    args = parser.parse_args()
    return args


def match(matchers, vm_name):
    """Check whether the given vm name matches any of the regex match objects

    Args:
        matchers (list): A list of regex objects with match() method
        vm_name (string): The name of the VM to compare
    Returns:
        bool: whether or not the vm_name is matched by ANY of the regex in the list
    """
    for matcher in matchers:
        if matcher.match(vm_name):
            return True
    else:
        return False


def scan_vm(provider_key, vm_name, delta, match_queue, non_match_queue, scan_failure_queue):
    """Scan an individual VM for age

    Args:
        provider_key (string): the provider key from yaml
        vm_name (string): name of the VM to scan
        delta (datetime.timedelta) The timedelta to compare age against for matches
        match_queue (Queue.Queue): MP queue to hold VMs matching age requirement
        non_match_queue (Queue.Queue): MP queue to hold VMS NOT matching age requirement
        scan_failure_queue (Queue.Queue): MP queue to hold vms that we could not compare age

    Returns:
        None: Uses the Queues to 'return' data
    """
    provider_mgmt = get_mgmt(provider_key)
    now = datetime.datetime.now(tz=pytz.UTC)
    # Nested exceptions to try and be safe about the scanned values and to get complete results
    failure = False
    messages = []
    status = NULL
    try:
        # Localize to UTC
        vm_creation_time = provider_mgmt.vm_creation_time(vm_name)
    except Exception:
        failure = True
        messages.append('{}: Exception getting creation time for {}'.format(provider_key, vm_name))
        # This VM must have some problem, include in report even though we can't delete
        try:
            status = provider_mgmt.vm_status(vm_name)
        except Exception:
            failure = True
            messages.append('{}: Exception getting status for {}'.format(provider_key, vm_name))
            status = NULL
    finally:
        if failure:
            for message in messages:
                logger.exception(message)
                print(message)
            scan_failure_queue.put([VmReport(provider_key, vm_name, FAIL, status, NULL)])
            return

    # None of this should raise exceptions
    vm_delta = now - vm_creation_time
    print('{}: VM {} age: {}'.format(provider_key, vm_name, vm_delta))
    data = VmData(provider_key, vm_name, str(vm_delta))

    # test age to determine which queue it goes in
    queue = match_queue if delta < vm_delta else non_match_queue
    queue.put([data])


def scan_provider(provider_key, matchers, delta, match_queue, scan_failure_queue):
    """
    Process the VMs on a given provider, comparing name and creation time.
    Append vms meeting criteria to vms_to_delete

    Args:
        provider_key (string): the provider key from yaml
        matchers (list): A list of regex objects with match() method
        delta (datetime.timedelta) The timedelta to compare age against for matches
        match_queue (Queue.Queue): MP queue to hold VMs matching age requirement
        scan_failure_queue (Queue.Queue): MP queue to hold vms that we could not compare age
    Returns:
        None: Uses the Queues to 'return' data
    """
    print('{}: scanning for matching VMs...'.format(provider_key))
    try:
        provider_mgmt = get_mgmt(provider_key)
        vm_list = provider_mgmt.list_vm()

        # don't really need to thread this, fast enough
        text_matched_vms = [name for name in vm_list if match(matchers, name)]
        non_text_matching = set(vm_list) - set(text_matched_vms)
        print('{}: NOT matching text filters: {}'.format(provider_key, non_text_matching))
        print('{}: Matching text filters: {}'.format(provider_key, text_matched_vms))

        # MP for vm scanning, could be many VMs per provider
        # match_queue is passed through and processed by this method's caller
        non_time_match_queue = Queue()
        vm_proc_list = []
        for vm_name in text_matched_vms:
            vm_proc_list.append(
                Process(target=scan_vm,
                        args=(provider_key, vm_name, delta, match_queue,
                              non_time_match_queue, scan_failure_queue)))

        for proc in vm_proc_list:
            proc.start()
        for proc in vm_proc_list:
            proc.join()

        # each item on scan_queue is a VmData tuple
        # process non_match_queue and log its contents now
        non_time_matching = []
        while not non_time_match_queue.empty():
            non_time_matching.extend(non_time_match_queue.get())

        print('{}: Finished scanning for matches'.format(provider_key))
        for non_match in non_time_matching:
            print('{}: VM {} matched text filters but not age: {}'
                  .format(provider_key, non_match.name, non_match.age))

    except Exception as ex:
        # Print out the error message too because logs in the job get deleted
        print('{}: scan exception ({}: {})'.format(provider_key, type(ex).__name__, str(ex)))
        logger.error('failed to scan vms from provider {}'.format(provider_key))
        logger.exception(ex)


def delete_provider_vm(provider_key, vm_name, age, queue):
    """ Delete the given vm_name from the provider via REST interface

    Args:
        provider_key (string): name of the provider from yaml
        vm_name (string): name of the vm to delete
        age (string): age of the VM to delete
        queue (Queue.Queue): MP Queue to store the VmReport tuple on delete result
    Returns:
        None: Uses the Queues to 'return' data
    """
    # diaper exceptions here to handle anything and continue.
    provider_mgmt = get_mgmt(provider_key)
    try:
        status = provider_mgmt.vm_status(vm_name)
    except Exception:  # noqa
        status = FAIL
        message = '{}: Exception getting status for {}'.format(provider_key, vm_name)
        print(message)
        logger.exception(message)

    print("{}: Deleting {}, age: {}, status: {}".format(provider_key, vm_name, age, status))
    try:
        # delete_vm returns boolean based on success
        if provider_mgmt.delete_vm(vm_name):
            message = '{}: Delete success: {}'.format(provider_key, vm_name)
            logger.info(message)
            result = PASS
        else:
            message = '{}: Delete failed: {}'.format(provider_key, vm_name)
            logger.error(message)
            result = FAIL
    except Exception:  # noqa
        result = FAIL  # set this here to cover anywhere the exception could happen
        message = '{}: Exception during delete: {}'.format(provider_key, vm_name)
        logger.exception(message)
    finally:
        print(message)
        queue.put([VmReport(provider_key, vm_name, age, status, result)])


def cleanup_vms(texts, max_hours=24, providers=None, prompt=True):
    """
    Main method for the cleanup process
    Generates regex match objects
    Checks providers for cleanup boolean in yaml
    Checks provider connectivity (using ping)
    Threads process_provider_vms to build list of vms to delete
    Prompts user to continue with delete
    Threads deleting of the vms

    Args:
        texts (list): List of regex strings to match with
        max_hours (int): age limit for deletion
        providers (list): List of provider keys to scan and cleanup
        prompt (bool): Whether or not to prompt the user before deleting vms
    Returns:
        int: return code, 0 on success, otherwise raises exception
    """
    providers = providers or list_provider_keys()
    delta = datetime.timedelta(hours=int(max_hours))
    # Compile regex, strip leading/trailing single quotes from cli arg
    matchers = [re.compile(text.strip("'"), re.IGNORECASE) for text in texts]
    print('Matching VM names against the following case-insensitive strings: {}'.format(texts))

    providers_to_scan = []
    for provider_key in providers:
        # check for cleanup boolean
        if not cfme_data['management_systems'][provider_key].get('cleanup', False):
            print('Skipping {}, cleanup map set to false or missing in yaml'.format(provider_key))
            continue
        # check the provider is reachable
        ipaddress = cfme_data['management_systems'][provider_key].get('ipaddress')
        if ipaddress and not net.is_pingable(ipaddress):
            continue
        # passed the checks
        providers_to_scan.append(provider_key)

    scan_queue = Queue()
    scan_failure_queue = Queue()
    scan_proc_list = []
    for provider_key in providers_to_scan:
        scan_proc_list.append(
            Process(target=scan_provider,
                    args=(provider_key, matchers, delta, scan_queue, scan_failure_queue)))

    for proc in scan_proc_list:
        proc.start()
    for proc in scan_proc_list:
        proc.join()

    # each item on scan_queue is a VmData tuple
    vms_to_delete = []
    while not scan_queue.empty():
        vms_to_delete.extend(scan_queue.get())

    if vms_to_delete and prompt:
        yesno = raw_input('Delete the-se VMs? [y/N]: ')
        if str(yesno).lower() != 'y':
            print('Exiting.')
            return 0

    if not vms_to_delete:
        print('No VMs to delete.')

    delete_queue = Queue()
    delete_proc_list = []
    for provider_key, vm_name, age in vms_to_delete:
        delete_proc_list.append(
            Process(target=delete_provider_vm,
                    args=(provider_key, vm_name, age, delete_queue)))

    for proc in delete_proc_list:
        proc.start()
    for proc in delete_proc_list:
        proc.join()

    deleted_vms_list = []
    while not delete_queue.empty():
        deleted_vms_list.extend(delete_queue.get())  # Each item is a VmReport tuple

    # Add in any machines that failed to scan for reporting
    while not scan_failure_queue.empty():
        deleted_vms_list.extend(scan_failure_queue.get())

    with open(args.outfile, 'a') as report:
        report.write('## VM/Instances deleted via:\n'
                     '##   text matches: {}\n'
                     '##   age matches: {}\n'
                     .format(texts, max_hours))
        message = tabulate(sorted(deleted_vms_list, key=attrgetter('result')),
                           headers=['Provider', 'Name', 'Age', 'Status Before', 'Delete RC'],
                           tablefmt='orgtbl')
        report.write(message + '\n')
    print(message)
    print("Deleting finished")

    return 0


if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(cleanup_vms(args.text_to_match, args.max_hours, args.providers, args.prompt))
