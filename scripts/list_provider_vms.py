import argparse
from tabulate import tabulate
from multiprocessing import Process, Queue

from wrapanapi.exceptions import VMError

from cfme.utils.conf import cfme_data
from cfme.utils.path import log_path
from cfme.utils.providers import get_mgmt, list_provider_keys


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
    parser.add_argument('provider',
                        default=None,
                        nargs='*',
                        help='Provider keys, can be user multiple times. If none are given '
                             'the script will use all providers from cfme_data or match tags')

    args = parser.parse_args()
    return args


def process_tags(provider_keys, tags=None):
    """
    Process the tags provided on command line to build a list of provider keys that match
    :param tags: list of tags to match against cfme_data
    :param provider_keys list of provider_keys to append to
    :return: list or provider keys matching tags
    """
    # Check for tags first, build list of provider_keys from it
    if tags:
        all_provider_keys = list_provider_keys()
        for key in all_provider_keys:
            # need to check tags list against yaml tags list for intersection of a single tag
            yaml_tags = cfme_data['management_systems'][key]['tags']
            if any(tag in tags for tag in yaml_tags):
                print('Matched tag from {} on provider {}:tags:{}'.format(tags, key, yaml_tags))
                provider_keys.add(key)


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
    try:
        vm_list = provider.list_vm()
    except NotImplementedError:
        print('Provider does not support list_vm: {}'.format(provider_key))
        output_list.append([provider_key, 'Not Supported', NULL, NULL, NULL])
        return
    else:
        # TODO thread metadata collection for further speed improvements
        for vm_name in vm_list:
            # Init these meta values in case they fail to query
            status, creation, vm_type = None, None, None
            try:
                print('Collecting metadata for VM {} on provider {}'.format(vm_name, provider_key))
                # VMError raised for some vms in bad status
                # exception message contains useful information about VM status
                try:
                    status = provider.vm_status(vm_name)
                except VMError as ex:
                    status = ex.message

                creation = provider.vm_creation_time(vm_name)

                # different provider types implement different methods to get instance type info
                try:
                    vm_type = provider.vm_type(vm_name)
                except (AttributeError, NotImplementedError):
                    vm_type = provider.vm_hardware_configuration(vm_name)
                finally:
                    vm_type = vm_type or '--'

            except Exception as ex:
                print('Exception during provider processing on {}: {}'
                      .format(provider_key, ex.message))
                continue
            finally:
                # Add the VM to the list anyway, we just might not have all metadata
                output_list.append([provider_key,
                                    vm_name,
                                    status or NULL,
                                    creation or NULL,
                                    str(vm_type) or NULL])

    output_queue.put(output_list)
    return


if __name__ == "__main__":
    args = parse_cmd_line()
    # providers as a set when processing tags to ensure unique entries
    providers = set(args.provider)
    process_tags(providers, args.tag)
    providers = providers or list_provider_keys()

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
