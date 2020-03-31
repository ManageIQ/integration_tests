#! /usr/bin/env python3
# uses Pool.starmap, which is py3 only
import argparse
import datetime
import re
import sys
from collections import namedtuple
from datetime import timedelta
from multiprocessing import Manager
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool
from operator import attrgetter

import pytz
from tabulate import tabulate
from wrapanapi.exceptions import VMInstanceNotFound

from cfme.utils.appliance import DummyAppliance
from cfme.utils.log import add_stdout_handler
from cfme.utils.log import logger
from cfme.utils.path import log_path
from cfme.utils.providers import get_mgmt
from cfme.utils.providers import list_providers
from cfme.utils.providers import ProviderFilter

# Constant strings for the report
PASS = 'PASS'
FAIL = 'FAIL'
NULL = '--'

VmProvider = namedtuple('VmProvider', 'provider_key, vm')
VmData = namedtuple('VmData', 'provider_key, vm, age')
VmReport = namedtuple('VmReport', 'provider_key, name, age, status, result')

# log to stdout too
add_stdout_handler(logger)

# manager for queues that can be shared
manager = Manager()


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('-f', '--force', default=True, action='store_false', dest='dryrun',
                        help='Do NOT dry-run (DANGER zone!)')
    parser.add_argument('--max-hours', default=24,
                        help='Max hours since the VM was created or last powered on '
                             '(varies by provider, default 24)')
    parser.add_argument('--provider', dest='providers', action='append', default=None,
                        help='Provider(s) to inspect, can be used multiple times.',
                        metavar='PROVIDER')
    parser.add_argument('--tag', dest='tags', action='append', default=None,
                        help='Tag to filter providers by, like "extcloud". '
                             'Can be used multiple times')
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


def cleanup_provider(provider_key, matchers, scan_failure_queue, max_hours, dryrun):
    """
    Process the VMs on a given provider, comparing name and creation time.
    Use thread pools to scan vms, then to delete vms in batches

    Args:
        provider_key (string): the provider key from yaml
        matchers (list): A list of regex objects with match() method
        scan_failure_queue (Queue.Queue): MP queue to hold vms that we could not compare age
    Returns:
        None: if there aren't any old vms to delete
        List of VMReport tuples
    """
    logger.info('%r: Start scan for vm text matches', provider_key)
    try:
        vm_list = get_mgmt(provider_key).list_vms()
    except Exception:  # noqa
        scan_failure_queue.put(VmReport(provider_key, FAIL, NULL, NULL, NULL))
        logger.exception('%r: Exception listing vms', provider_key)
        return

    text_matched_vms = [vm for vm in vm_list if match(matchers, vm.name)]

    logger.info('%r: NOT matching text filters: %r',
                provider_key,
                {v.name for v in vm_list} - {v.name for v in text_matched_vms})
    logger.info('%r: MATCHED text filters: %r', provider_key, [vm.name for vm in text_matched_vms])

    if not text_matched_vms:
        return

    with ThreadPool(4) as tp:
        scan_args = (
            (provider_key,
             vm,
             timedelta(hours=int(max_hours)),
             scan_failure_queue)
            for vm in text_matched_vms
        )
        old_vms = [
            vm
            for vm in tp.starmap(scan_vm, scan_args)
            if vm is not None
        ]

    if old_vms and dryrun:
        logger.warning('DRY RUN: Would have deleted the following VMs on provider %s: \n %s',
                       provider_key,
                       [(vm[0].name, vm[1], vm[2]) for vm in old_vms])
        # for tabulate consistency on dry runs. 0=vm, 1=age, 2=status
        return [VmReport(provider_key, vm[0].name, vm[1], vm[2], NULL) for vm in old_vms]

    elif old_vms:
        with ThreadPool(4) as tp:
            delete_args = (
                (provider_key,
                 old_tuple[0],  # vm
                 old_tuple[1])  # age
                for old_tuple in old_vms
            )
            delete_results = tp.starmap(delete_vm, delete_args)

            return delete_results


def scan_vm(provider_key, vm, delta, scan_failure_queue):
    """Scan an individual VM for age

    Args:
        vm (obj) wrapanapi vm object
        delta (datetime.timedelta) The timedelta to compare age against for matches
        match_queue (Queue.Queue): MP queue to hold VMs matching age requirement
        scan_failure_queue (Queue.Queue): MP queue to hold vms that we could not compare age

    Returns:
        None: Uses the Queues to 'return' data
    """
    now = datetime.datetime.now(tz=pytz.UTC)
    # Nested exceptions to try and be safe about the scanned values and to get complete results
    failure = False
    status = NULL

    logger.info('%r: Scan VM %r...', provider_key, vm.name)
    # set default here in case exceptions cause vm_creation_time to not be set
    vm_creation_time = datetime.datetime(2018, 1, 1, 0, 0).replace(tzinfo=pytz.UTC)
    # get creation time
    try:
        vm_creation_time = vm.creation_time or vm_creation_time  # could be None, use the default
    except VMInstanceNotFound:
        logger.exception('%r: could not locate VM %s', provider_key, vm.name)
        failure = True
        pass
    except Exception:  # noqa
        logger.exception('%r: Exception getting creation time for %r', provider_key, vm.name)
        failure = True
        # get state of vm that doesn't have creation time
        try:
            status = vm.state
        except Exception:  # noqa
            logger.exception('%r: Exception getting status for %r', provider_key, vm.name)
            status = NULL
            pass
        pass

    if failure:
        scan_failure_queue.put(VmReport(provider_key, vm.name, FAIL, status, NULL))

    vm_delta = now - vm_creation_time
    logger.info('%r: VM %r age: %s', provider_key, vm.name, vm_delta)

    # test age to determine which queue it goes in
    if delta < vm_delta:
        logger.info('%r: VM %r MATCHED age requirement', provider_key, vm.name)
        return (vm, vm_delta, status)
    else:
        logger.info('%r: VM %r did not match age requirement', provider_key, vm.name)


def delete_vm(provider_key, vm, age):
    """ Delete the given vm from the provider via REST interface

    Args:
        provider_key (string): name of the provider from yaml
        vm (object): wrapanapi vm object to delete
        age (datetime.timedelta): age of the VM to delete
    Returns:
        VmReport of the delete attempt result and status of the vm
    """
    # diaper exceptions here to handle anything and continue.
    try:
        status = vm.state
    except Exception:  # noqa
        status = FAIL
        logger.exception('%r: Exception getting status for %r', provider_key, vm.name)
        # keep going, try to delete anyway

    logger.info("%r: Deleting %r, age: %r, status: %r", provider_key, vm.name, age, status)
    try:
        # delete vm returns boolean based on success
        if vm.cleanup():
            result = PASS
            logger.info('%r: Delete success: %r', provider_key, vm.name)
        else:
            result = FAIL
            logger.error('%r: Delete failed: %r', provider_key, vm.name)
    except Exception:  # noqa
        # TODO vsphere delete failures, workaround for wrapanapi issue #154
        if not vm.exists:
            # The VM actually has been deleted
            result = PASS
        else:
            result = FAIL  # set this here to cover anywhere the exception could happen
        logger.exception('%r: Exception during delete: %r, double check result: %r',
                         provider_key, vm.name, result)
    finally:
        return VmReport(provider_key, vm.name, age, status, result)


def cleanup_vms(texts, max_hours=24, providers=None, tags=None, dryrun=True):
    """
    Main method for the cleanup process
    Generates regex match objects
    Checks providers for cleanup boolean in yaml
    Checks provider connectivity (using ping)
    Process Pool for provider scanning
    Each provider process will thread vm scanning and deletion

    Args:
        texts (list): List of regex strings to match with
        max_hours (int): age limit for deletion
        providers (list): List of provider keys to scan and cleanup
        tags (list): List of tags to filter providers by
        dryrun (bool): Whether or not to actually delete VMs or just report
    Returns:
        int: return code, 0 on success, otherwise raises exception
    """
    logger.info('Matching VM names against the following case-insensitive strings: %r', texts)
    # Compile regex, strip leading/trailing single quotes from cli arg
    matchers = [re.compile(text.strip("'"), re.IGNORECASE) for text in texts]

    # setup provider filter with cleanup (default), tags, and providers (from cli opts)
    filters = [ProviderFilter(required_fields=[('cleanup', True)])]
    if tags:
        logger.info('Adding required_tags ProviderFilter for: %s', tags)
        filters.append(ProviderFilter(required_tags=tags))
    if providers:
        logger.info('Adding keys ProviderFilter for: %s', providers)
        filters.append(ProviderFilter(keys=providers))

    # Just want keys, use list_providers with no global filters to include disabled.
    with DummyAppliance():
        providers_to_scan = [prov.key for prov in list_providers(filters, use_global_filters=False)]
    logger.info('Potential providers for cleanup, filtered with given tags and provider keys: \n%s',
                '\n'.join(providers_to_scan))

    # scan providers for vms with name matches
    scan_fail_queue = manager.Queue()
    with Pool(4) as pool:
        deleted_vms = pool.starmap(
            cleanup_provider,
            ((provider_key, matchers, scan_fail_queue, max_hours, dryrun)
             for provider_key in providers_to_scan)
        )

    # flatten deleted_vms list, as its top level is by provider process
    # at same time remove None responses
    deleted_vms = [report
                   for prov_list in deleted_vms if prov_list is not None
                   for report in prov_list]

    scan_fail_vms = []
    # add the scan failures into deleted vms for reporting sake
    while not scan_fail_queue.empty():
        scan_fail_vms.append(scan_fail_queue.get())

    with open(args.outfile, 'a') as report:
        report.write('## VM/Instances deleted via:\n'
                     '##   text matches: {}\n'
                     '##   age matches: {}\n'
                     .format(texts, max_hours))
        message = tabulate(
            sorted(scan_fail_vms + deleted_vms, key=attrgetter('result')),
            headers=['Provider', 'Name', 'Age', 'Status Before', 'Delete RC'],
            tablefmt='orgtbl'
        )
        report.write(message + '\n')
    logger.info(message)
    return 0


if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(cleanup_vms(args.text_to_match, args.max_hours, args.providers, args.tags,
                         args.dryrun))
