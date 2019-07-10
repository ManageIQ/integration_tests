#!/usr/bin/env python3
import argparse
from multiprocessing import Process
from multiprocessing import Queue

from tabulate import tabulate

from cfme.utils.appliance import DummyAppliance
from cfme.utils.path import log_path
from cfme.utils.providers import get_mgmt
from cfme.utils.providers import list_providers
from cfme.utils.providers import ProviderFilter


# Constant for report
NULL = '--'


def parse_cmd_line():
    """
    Specify and parse arguments
    :return: args, kwargs, the usual
    """
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--outfile',
                        default=log_path.join('list_provider_vms.log').strpath,
                        dest='outfile')
    parser.add_argument('--tag',
                        default=None,
                        dest='tag',
                        action='append',
                        help='A provider tag to match a group of providers instead of all '
                             'providers from cfme_data. Can be used multiple times')
    parser.add_argument('--provider',
                        default=None,
                        action='append',
                        help='Provider keys, can be user multiple times. If none are given '
                             'the script will use all providers from cfme_data or match tags')

    args = parser.parse_args()
    return args


def list_vms(provider_key, output_queue):
    """
    List all the vms/instances on the given provider key
    Build list of lists with basic vm info: [[provider, vm, status, age, type], [etc]]
    :param provider_key: string provider key
    :param output_queue: a multiprocessing.Queue object to add results to
    :return: list of lists of vms and basic statistics
    """
    output_list = []

    print('Listing VMS on provider {}'.format(provider_key))
    provider = get_mgmt(provider_key)
    # TODO thread metadata collection for further speed improvements
    for vm in provider.list_vms():
        # Init these meta values in case they fail to query
        status, creation, vm_type = None, None, None
        try:
            print('Collecting metadata for VM {} on provider {}'.format(vm.name, provider_key))
            status = vm.state
            creation = vm.creation_time

            # different provider types implement different methods to get instance type info
            if hasattr(vm, 'type'):
                vm_type = vm.type
            else:
                try:
                    vm_type = vm.get_hardware_configuration()
                except (AttributeError, NotImplementedError):
                    vm_type = '--'

        except Exception as ex:
            print('Exception during provider processing on {}: {}'
                  .format(provider_key, ex.message))
            continue
        finally:
            # Add the VM to the list anyway, we just might not have all metadata
            output_list.append([provider_key,
                                vm.name,
                                status or NULL,
                                creation or NULL,
                                str(vm_type) or NULL])

    output_queue.put(output_list)
    return


if __name__ == "__main__":
    args = parse_cmd_line()
    # providers as a set when processing tags to ensure unique entries
    filters = []
    if args.provider:
        filters.append(ProviderFilter(keys=args.provider))
    if args.tag:
        filters.append(ProviderFilter(required_tags=args.tag))

    # don't include global filter to keep disabled in the list
    with DummyAppliance('5.10.0.0'):
        providers = [prov.key for prov in list_providers(filters, use_global_filters=False)]

    queue = Queue()  # for MP output
    proc_list = [
        Process(target=list_vms, args=(provider, queue), name='list_vms:{}'.format(provider))
        for provider in providers
    ]
    for proc in proc_list:
        proc.start()
    for proc in proc_list:
        proc.join()

    print('Done processing providers, assembling report...')

    # Now pull all the results off of the queue
    # Stacking the generator this way is equivalent to using list.extend instead of list.append
    # Need to check queue.empty since a call to get will raise an Empty exception
    output_data = []
    while not queue.empty():
        output_data.extend(queue.get())

    header = '''## VM/Instances on providers matching:
## providers: {}
## tags: {}
'''.format(args.provider, args.tag)  # don't forget trailing newline...

    with open(args.outfile, 'w') as output_file:
        # stdout and the outfile
        output_file.write(header)
        print(header)

        report = tabulate(output_data,
                          headers=['Provider', 'VM', 'Status', 'Created On', 'Type/Hardware'],
                          tablefmt='orgtbl')

        output_file.write(report)
        print(report)
