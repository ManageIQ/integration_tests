#!/usr/bin/env python3
import argparse
import re
import sys
from collections import defaultdict

from cfme.utils.conf import credentials
from cfme.utils.config_data import cfme_data
from cfme.utils.log import add_stdout_handler
from cfme.utils.log import logger
from cfme.utils.providers import get_mgmt
from cfme.utils.providers import list_provider_keys
from cfme.utils.ssh import SSHClient


add_stdout_handler(logger)  # log to stdout


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--provider', dest='provider', default=None,
        help='Provider to list the unregistered files')
    args = parser.parse_args()
    return args


def list_orphaned_files_per_host(host_name, host_datastore_urls, provider_key, vm_registered_files,
                                 unregistered_files):
    try:
        providers_data = cfme_data.get("management_systems", {})
        hosts = providers_data[provider_key]['hosts']
        hostname = [host['name'] for host in hosts if host_name in host['name']]
        # check if hostname returned is ipaddress
        if not hostname:
            hostname = re.findall(r'[0-9]+(?:\.[0-9]+){3}', host_name)
        connect_kwargs = {
            'username': credentials['host_default']['username'],
            'password': credentials['host_default']['password'],
            'hostname': hostname[0]
        }
        with SSHClient(**connect_kwargs) as ssh_client:
            for datastore_url in host_datastore_urls:
                datastore_path = re.findall(r'([^ds:`/*].*)', str(datastore_url))

                command = 'ls ~/{}'.format(datastore_path[0])
                result = ssh_client.run_command(command)
                files_in_datastore = result.output.splitlines() if result.success else []
                for fil in files_in_datastore:
                    if fil not in vm_registered_files:
                        file_type = 'UNKNOWN'
                        number_of_files = 0
                        command = 'test -d ~/{}/{}; echo $?'.format(datastore_path[0], fil)
                        result = ssh_client.run_command(command)
                        file_extension = re.findall(r'.*\.(\w*)', fil)
                        if file_extension:
                            file_type = file_extension[0]
                            number_of_files = 1
                        if int(result.output.strip()) == 0:
                            command = 'ls ~/{}/{} | wc -l'.format(datastore_path[0], fil)
                            result = ssh_client.run_command(command)
                            number_of_files = result.output.strip()
                            command = 'find ~/{}/{} -name "*.vmx" | wc -l'.format(
                                datastore_path[0], fil)
                            vmx_result = ssh_client.run_command(command)
                            command = 'find ~/{}/{} -name "*.vmtx" | wc -l'.format(
                                datastore_path[0], fil)
                            vmtx_result = ssh_client.run_command(command)
                            command = 'find ~/{}/{} -name "*.vmdk" | wc -l'.format(
                                datastore_path[0], fil)
                            vmdk_result = ssh_client.run_command(command)

                            if int(vmx_result.output.strip()) > 0:
                                file_type = 'VirtualMachine'
                            elif int(vmtx_result.output.strip()) > 0:
                                file_type = 'Template'
                            elif int(vmdk_result.output.strip()) > 0:
                                file_type = 'VMDK'
                                # delete_this = '~/' + datastore_path[0] + fil
                                # command = 'rm -rf {}'.format(delete_this)
                                # result = ssh_client.run_command(command)
                                # logger.info(result.output)

                        file_path = '~/' + datastore_path[0] + fil
                        if file_path not in unregistered_files:
                            unregistered_files.append(file_path)
                            logger.info(
                                '{host}\t\t{path}\t\t{ftype}\t\t{num}'
                                .format(
                                    host=hostname[0],
                                    path=file_path,
                                    ftype=file_type,
                                    num=number_of_files
                                )
                            )

    except Exception:
        logger.exception('Exception listing orphaned files per host')
        return False


def get_registered_vm_files(provider_key):
    try:
        logger.info("%s processing all the registered files..", provider_key)
        vm_registered_files = defaultdict(set)
        provider = get_mgmt(provider_key)
        for vm in provider.list_vms():
            try:
                vm_file_path = vm.get_config_files_path()
                vm_directory_name = re.findall(r'\s(.*)/\w*', vm_file_path)
                vm_registered_files[vm_directory_name[0]] = vm.name
            except Exception:
                logger.exception('Failed to get creation/boot time for %s on %s',
                                 vm.name, provider_key)
                continue
        logger.info("\n**************************REGISTERED FILES ON %s***********************\n",
                    provider_key)
        for k, v in vm_registered_files.items():
            logger.info('FILE_NAME: %s\nVM_NAME: %s\n', k, v)
        return vm_registered_files
    except Exception:
        logger.exception('failed to process vms from provider %s', provider_key)


def get_datastores_per_host(provider_key):
    logger.info('%s processing to get datastores per host', provider_key)
    try:
        provider = get_mgmt(provider_key)

        vm_registered_files = get_registered_vm_files(provider_key)
        hosts = provider.list_host()
        host_datastore_url = {host: provider.list_host_datastore_url(host) for host in hosts}
        unregistered_files = []

        logger.info("\n*********************UNREGISTERED FILES ON: %s**********************\n",
                    provider_key)
        logger.info('HOST_NAME\t\tFILE_PATH\t\tTEMPLATE_VM_ISO\t\tNUMBER_OF_FILES\n')
        for host in host_datastore_url:
            try:
                list_orphaned_files_per_host(host, host_datastore_url[host],
                                             provider_key, vm_registered_files,
                                             unregistered_files)
            except Exception:
                logger.exception('Exception calling list_orphaned_files_per_host')
                continue

    except Exception:
        logger.exception('failed to process vms from provider %s', provider_key)


def get_orphaned_vmware_files(provider=None):
    providers = [provider] if provider else list_provider_keys("virtualcenter")

    for provider_key in providers:
        # we can add thread here
        get_datastores_per_host(provider_key)


if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(get_orphaned_vmware_files(args.provider))
