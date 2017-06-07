#!/usr/bin/env python2

import argparse
import datetime
import pytz
import re
import sys
from os.path import join as pathjoin
from collections import defaultdict, namedtuple
from dateutil import parser
from tabulate import tabulate
from threading import Lock, Thread
from tzlocal import get_localzone
from mgmtsystem.virtualcenter import VMWareSystem

from utils import net
from utils.log import logger
from utils.conf import cfme_data, credentials
from utils.path import log_path
from utils.ssh import SSHClient
from utils.providers import list_provider_keys, get_mgmt

lock = Lock()
# Hold all the deleted vm's as a list, add in from all the threads with lock
# Each items is a list containing: ['Provider', 'Name', 'Age', 'Status From Provider', 'Delete RC']
deleted_vms_list = []

# Constant strings for the report
PASS = 'PASS'
FAIL = 'FAIL'
NULL = '--'

NameAge = namedtuple('NameAge', 'name, age')
HostCreds = namedtuple('HostCreds', 'hostname, cred_key')


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
    parser.add_argument('-l', '--list', default=False, action='store_true', dest='list_vms',
                        help='list vms of the specified "provider_type"')
    parser.add_argument('--provider-type', dest='provider_type', default='ec2, gce, azure',
                        help='comma separated list of the provider type, useful in case of gce,'
                             'azure, ec2 to get the insight into cost/vm listing')
    parser.add_argument('--outfile', dest='outfile',
                        default=log_path.join('cleanup_old_vms.log').strpath,
                        help='outfile to list ')
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


def get_vm_config_modified_time(host_name, vm_name, datastore_url, provider_key):
    """
    SSH to provider and find modified date for VMX file
    :param host_name: string the host to connect to
    :param vm_name: string name of the vm
    :param datastore_url: string datastore url in format ds:
    :param provider_key: string provider key
    :return:
    """
    try:
        providers_data = cfme_data.get("management_systems", {})
        yaml_hosts = providers_data[provider_key]['hosts']
        # pull host name and credentials from yaml, may be multiple hosts defined
        hostname, host_cred_key = None, None  # Init in case not found in yaml
        for host in yaml_hosts:
            # Some of the vsphere environments are configured with IP as the host's name
            if host_name in [host['name'], host.get('ipaddress')]:
                hostname, host_cred_key = host['name'], host['credentials']
                break

        if not hostname or not host_cred_key:
            raise KeyError('Could not find host {} and credentials for {} in yaml'
                           .format(host_name, provider_key))
        connect_kwargs = {
            'username': credentials[host_cred_key]['username'],
            'password': credentials[host_cred_key]['password'],
            'hostname': hostname
        }
        datastore_path = re.findall(r'([^ds:`/*].*)', str(datastore_url))
        command = 'find ~/{} -name {}.vmx | xargs  date -r'.format(
            pathjoin(datastore_path[0], vm_name),
            vm_name)

        with SSHClient(**connect_kwargs) as ssh_client:
            result = ssh_client.run_command(command)
        parsed_time = parser.parse(str(result).rstrip())
        return parsed_time.astimezone(pytz.timezone(str(get_localzone()))).replace(tzinfo=None)
    except Exception as e:
        logger.error(e)
        return False


def process_provider_vms(provider_key, matchers, delta, vms_to_delete):
    """
    Process the VMs on a given provider, comparing name and creation time.
    Append vms meeting criteria to vms_to_delete

    :param provider_key: string provider key
    :param matchers: matching strings
    :param delta: time delta
    :param vms_to_delete: the list of vms that should be deleted
    :return: modifies vms_to_delete
    """
    with lock:
        print('{} processing'.format(provider_key))
    try:
        now = datetime.datetime.now()
        with lock:
            # Known conf issue :)
            provider = get_mgmt(provider_key)
        vm_list = provider.list_vm()

        for vm_name in vm_list:
            try:
                if not match(matchers, vm_name):
                    continue

                if (isinstance(provider, VMWareSystem) and
                        provider.vm_status(vm_name) == 'poweredOff'):
                    hostname = provider.get_vm_host_name(vm_name)
                    vm_config_datastore = provider.get_vm_config_files_path(vm_name)
                    datastore_url = provider.get_vm_datastore_path(vm_name, vm_config_datastore)
                    vm_creation_time = get_vm_config_modified_time(hostname, vm_name,
                                                                   datastore_url, provider_key)
                else:
                    vm_creation_time = provider.vm_creation_time(vm_name)

                if vm_creation_time is False:
                    # This VM must have some problem, include in report even though we can't delete
                    status = provider.vm_status(vm_name)
                    deleted_vms_list.append([provider_key,
                                             vm_name,
                                             NULL,  # can't know age, failed getting creation date
                                             status,
                                             FAIL])
                    raise Exception  # the except block message is accurate in this case

                if vm_creation_time + delta < now:
                    vm_delta = now - vm_creation_time
                    with lock:
                        vms_to_delete[provider_key].add((vm_name, vm_delta))
            except Exception as e:
                logger.error(e)
                logger.error('Failed to get creation/boot time for {} on {}'.format(
                    vm_name, provider_key))
                continue

        with lock:
            print('{} finished'.format(provider_key))
    except Exception as ex:
        with lock:
            # Print out the error message too because logs in the job get deleted
            print('{} failed ({}: {})'.format(provider_key, type(ex).__name__, str(ex)))
        logger.error('failed to process vms from provider {}'.format(provider_key))
        logger.exception(ex)


def delete_provider_vms(provider_key, provider_mgmt, names_ages):
    """
    lock, lock, more locking. Need to convert caller to Process+Queue

    :param provider_key: string provider name/key, for easy logging
    :param provider_mgmt: provider mgmtsystem object
    :param names_ages: list of NameAge namedtuples
    :return: none
    """
    with lock:
        print('Deleting VMs from {} ...'.format(provider_key))

    for vm_name, age in names_ages:
        with lock:
            print("Deleting {} from {}".format(vm_name, provider_key))
        try:
            provider_mgmt.delete_vm(vm_name)
            status = NULL
            result = PASS
        except Exception as e:
            status = provider_mgmt.vm_status(vm_name)
            result = FAIL
            with lock:
                print('Failed to delete {} on {}'.format(vm_name, provider_key))
                logger.exception(e)
        finally:
            with lock:
                deleted_vms_list.append([provider_key, vm_name, age, status, result])
    with lock:
        print("{} is done!".format(provider_key))


def cleanup_vms(texts, max_hours=24, providers=None, prompt=True):
    """
    Main method for the cleanup process
    Generates regex match objects
    Checks providers for cleanup boolean in yaml
    Checks provider connectivity (using ping)
    Threads process_provider_vms to build list of vms to delete
    Prompts user to continue with delete
    Threads deleting of the vms

    :param texts: list of strings to match against
    :param max_hours: integer maximum number of hours that the VM can exist for
    :param providers: list of provider keys
    :param prompt: boolean, whether or not to prompt the user for each delete
    :return: 0 if user declines delete when prompt is True
    """
    providers = providers or list_provider_keys()
    delta = datetime.timedelta(hours=int(max_hours))
    vms_to_delete = defaultdict(set)
    thread_queue = []
    # precompile regexes
    matchers = [re.compile(text, re.IGNORECASE) for text in texts]
    print('Matching VM names against the following case-insensitive strings: {}'.format(texts))

    for provider_key in providers:
        # check for cleanup boolean
        if not cfme_data['management_systems'][provider_key].get('cleanup', False):
            print('Skipping {}, cleanup map set to false or missing in yaml'.format(provider_key))
            continue
        ipaddress = cfme_data['management_systems'][provider_key].get('ipaddress')
        if ipaddress and not net.is_pingable(ipaddress):
            continue
        thread = Thread(target=process_provider_vms,
                        args=(provider_key, matchers, delta, vms_to_delete))
        # Mark as daemon thread for easy-mode KeyboardInterrupt handling
        thread.daemon = True
        thread_queue.append(thread)
        thread.start()

    # Join the queued calls
    for thread in thread_queue:
        thread.join()

    if vms_to_delete and prompt:
        yesno = raw_input('Delete these VMs? [y/N]: ')
        if str(yesno).lower() != 'y':
            print('Exiting.')
            return 0

    if not vms_to_delete:
        print('No VMs to delete.')

    thread_queue = []
    for provider_key, vm_set in vms_to_delete.items():
        provider_mgmt = get_mgmt(provider_key)

        names_ages = []
        for vm_name, vm_delta in vm_set:
            days, hours = vm_delta.days, vm_delta.seconds / 3600
            age = '{} days, {} hours old'.format(days, hours)
            names_ages.append(NameAge(vm_name, age))

        thread = Thread(target=delete_provider_vms,
                        args=(provider_key, provider_mgmt, names_ages))
        # Mark as daemon thread for easy-mode KeyboardInterrupt handling
        thread.daemon = True
        thread_queue.append(thread)
        thread.start()

    for thread in thread_queue:
        thread.join()

    with open(args.outfile, 'w') as report:
        report.write('## VM/Instances deleted via:\n'
                     '##   text matches: {}\n'
                     '##   age matches: {}\n'
                     .format(texts, max_hours))
        message = tabulate(deleted_vms_list,
                           headers=['Provider', 'Name', 'Age', 'Status', 'Delete RC'],
                           tablefmt='orgtbl')
        report.write(message)
    print(message)

    print("Deleting finished")


if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(cleanup_vms(args.text_to_match, args.max_hours, args.providers, args.prompt))
