#!/usr/bin/env python2
import argparse
import datetime
from datetime import timedelta
import re
import sys
from collections import namedtuple
from operator import attrgetter
from multiprocessing import Manager, Pool

import pytz
from tabulate import tabulate

from cfme.utils.log import logger, add_stdout_handler
from cfme.utils.conf import cfme_data
from cfme.utils.path import log_path
from cfme.utils.providers import list_provider_keys, get_mgmt

# Constant strings for the report
PASS = 'PASS'
FAIL = 'FAIL'
NULL = '--'

VmProvider = namedtuple('VmProvider', 'provider_key, name')
VmData = namedtuple('VmData', 'provider_key, name, age')
VmReport = namedtuple('VmReport', 'provider_key, name, age, status, result')

# log to stdout too
add_stdout_handler(logger)

# manager for queues that can be shared
manager = Manager()


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


def pool_manager(func, arg_list):
    """Create a process pool and join the processes via apply_async

    Notes:
        Use Manager.Queue for any queues in the arg_list tuples.
        BLOCKS by joining

    # TODO put this into some utility library and handle kwargs, take pool size arg
    Args:
        func (method): A function to parallel process
        arg_list (list): a list of arg tuples

    Returns:
        list of the return values from apply_async
    """
    # TODO increase pool size
    proc_pool = Pool(8)
    proc_results = []
    for arg_tuple in arg_list:
        proc_results.append(proc_pool.apply_async(func, args=arg_tuple))
    proc_pool.close()
    proc_pool.join()

    # Check for exceptions since they're captured
    # Don't care about non-exception results since all non-exception results are in the queues
    results = []
    for proc_result in proc_results:
        try:
            result = proc_result.get()
        except Exception as ex:
            result = ex
        finally:
            if isinstance(result, Exception):
                logger.exception('Exception during function call %r', func.__name__)
            results.append(result)

    return results


def scan_provider(provider_key, matchers, match_queue, scan_failure_queue):
    """
    Process the VMs on a given provider, comparing name and creation time.
    Append vms meeting criteria to vms_to_delete

    Args:
        provider_key (string): the provider key from yaml
        matchers (list): A list of regex objects with match() method
        match_queue (Queue.Queue): MP queue to hold VMs matching age requirement
        scan_failure_queue (Queue.Queue): MP queue to hold vms that we could not compare age
    Returns:
        None: Uses the Queues to 'return' data
    """
    logger.info('%r: Start scan for vm text matches', provider_key)
    try:
        vm_list = get_mgmt(provider_key).list_vm()
    except Exception:  # noqa
        scan_failure_queue.put(VmReport(provider_key, FAIL, NULL, NULL, NULL))
        logger.exception('%r: Exception listing vms', provider_key)
        return

    text_matched_vms = [name for name in vm_list if match(matchers, name)]
    for name in text_matched_vms:
        match_queue.put(VmProvider(provider_key, name))

    non_text_matching = set(vm_list) - set(text_matched_vms)
    logger.info('%r: NOT matching text filters: %r', provider_key, non_text_matching)
    logger.info('%r: MATCHED text filters: %r', provider_key, text_matched_vms)


def scan_vm(provider_key, vm_name, delta, match_queue, scan_failure_queue):
    """Scan an individual VM for age

    Args:
        provider_key (string): the provider key from yaml
        vm_name (string): name of the VM to scan
        delta (datetime.timedelta) The timedelta to compare age against for matches
        match_queue (Queue.Queue): MP queue to hold VMs matching age requirement
        scan_failure_queue (Queue.Queue): MP queue to hold vms that we could not compare age

    Returns:
        None: Uses the Queues to 'return' data
    """
    provider_mgmt = get_mgmt(provider_key)
    now = datetime.datetime.now(tz=pytz.UTC)
    # Nested exceptions to try and be safe about the scanned values and to get complete results
    failure = False
    status = NULL
    logger.info('%r: Scan VM %r...', provider_key, vm_name)
    try:
        # Localize to UTC
        vm_creation_time = provider_mgmt.vm_creation_time(vm_name)
    except Exception:  # noqa
        failure = True
        logger.exception('%r: Exception getting creation time for %r', provider_key, vm_name)
        # This VM must have some problem, include in report even though we can't delete
        try:
            status = provider_mgmt.vm_status(vm_name)
        except Exception:  # noqa
            failure = True
            logger.exception('%r: Exception getting status for %r', provider_key, vm_name)
            status = NULL
    finally:
        if failure:
            scan_failure_queue.put(VmReport(provider_key, vm_name, FAIL, status, NULL))
            return

    vm_delta = now - vm_creation_time
    logger.info('%r: VM %r age: %r', provider_key, vm_name, vm_delta)
    data = VmData(provider_key, vm_name, str(vm_delta))

    # test age to determine which queue it goes in
    if delta < vm_delta:
        match_queue.put(data)
    else:
        logger.info('%r: VM %r did not match age requirement', provider_key, vm_name)


def delete_vm(provider_key, vm_name, age, result_queue):
    """ Delete the given vm_name from the provider via REST interface

    Args:
        provider_key (string): name of the provider from yaml
        vm_name (string): name of the vm to delete
        age (string): age of the VM to delete
        result_queue (Queue.Queue): MP Queue to store the VmReport tuple on delete result
    Returns:
        None: Uses the Queues to 'return' data
    """
    # diaper exceptions here to handle anything and continue.
    provider_mgmt = get_mgmt(provider_key)
    try:
        status = provider_mgmt.vm_status(vm_name)
    except Exception:  # noqa
        status = FAIL
        logger.exception('%r: Exception getting status for %r', provider_key, vm_name)

    logger.info("%r: Deleting %r, age: %r, status: %r", provider_key, vm_name, age, status)
    try:
        # delete_vm returns boolean based on success
        if provider_mgmt.delete_vm(vm_name):
            result = PASS
            logger.info('%r: Delete success: %r', provider_key, vm_name)
        else:
            result = FAIL
            logger.error('%r: Delete failed: %r', provider_key, vm_name)
    except Exception:  # noqa
        # TODO vsphere delete failures, workaround for wrapanapi issue #154
        if vm_name not in provider_mgmt.list_vm():
            # The VM actually has been deleted
            result = PASS
        else:
            result = FAIL  # set this here to cover anywhere the exception could happen
        logger.exception('%r: Exception during delete: %r, double check result: %r',
                         provider_key, vm_name, result)
    finally:
        result_queue.put(VmReport(provider_key, vm_name, age, status, result))


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
    logger.info('Matching VM names against the following case-insensitive strings: %r', texts)
    # Compile regex, strip leading/trailing single quotes from cli arg
    matchers = [re.compile(text.strip("'"), re.IGNORECASE) for text in texts]

    providers_to_scan = []
    for provider_key in providers or list_provider_keys():
        # check for cleanup boolean
        if not cfme_data['management_systems'][provider_key].get('cleanup', False):
            logger.info('SKIPPING %r, cleanup set to false or missing in yaml', provider_key)
            continue
        logger.info('SCANNING %r', provider_key)
        providers_to_scan.append(provider_key)

    # scan providers for vms with name matches
    # manager = Manager()
    text_match_queue = manager.Queue()
    scan_fail_queue = manager.Queue()
    provider_scan_args = [
        (provider_key, matchers, text_match_queue, scan_fail_queue)
        for provider_key in providers_to_scan]
    pool_manager(scan_provider, provider_scan_args)

    text_matched = []
    while not text_match_queue.empty():
        text_matched.append(text_match_queue.get())

    # scan vms for age matches
    age_match_queue = manager.Queue()
    vm_scan_args = [
        (provider_key, vm_name, timedelta(hours=int(max_hours)), age_match_queue, scan_fail_queue)
        for provider_key, vm_name in text_matched]
    pool_manager(scan_vm, vm_scan_args)

    vms_to_delete = []
    while not age_match_queue.empty():
        vms_to_delete.append(age_match_queue.get())

    scan_fail_vms = []
    # add the scan failures into deleted vms for reporting sake
    while not scan_fail_queue.empty():
        scan_fail_vms.append(scan_fail_queue.get())

    if vms_to_delete and prompt:
        yesno = raw_input('Delete these VMs? [y/N]: ')
        if str(yesno).lower() != 'y':
            logger.info('Exiting.')
            return 0

    # initialize this even if we don't have anything to delete, for report consistency
    deleted_vms = []
    if vms_to_delete:
        delete_queue = manager.Queue()
        delete_vm_args = [(provider_key, vm_name, age, delete_queue)
                          for provider_key, vm_name, age in vms_to_delete]
        pool_manager(delete_vm, delete_vm_args)

        while not delete_queue.empty():
            deleted_vms.append(delete_queue.get())  # Each item is a VmReport tuple

    else:
        logger.info('No VMs to delete.')

    with open(args.outfile, 'a') as report:
        report.write('## VM/Instances deleted via:\n'
                     '##   text matches: {}\n'
                     '##   age matches: {}\n'
                     .format(texts, max_hours))
        message = tabulate(sorted(scan_fail_vms + deleted_vms, key=attrgetter('result')),
                           headers=['Provider', 'Name', 'Age', 'Status Before', 'Delete RC'],
                           tablefmt='orgtbl')
        report.write(message + '\n')
    logger.info(message)
    return 0


if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(cleanup_vms(args.text_to_match, args.max_hours, args.providers, args.prompt))
