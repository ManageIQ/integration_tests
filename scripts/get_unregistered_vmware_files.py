#!/usr/bin/env python2

import argparse
import re
import sys
from collections import defaultdict

from utils.log import logger
from utils.conf import cfme_data
from utils.conf import credentials
from utils.ssh import SSHClient
from utils.providers import list_provider_keys, get_mgmt


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
        for datastore_url in host_datastore_urls:
            datastore_path = re.findall(r'([^ds:`/*].*)', str(datastore_url))
            ssh_client = SSHClient(**connect_kwargs)
            command = 'ls ~/{}'.format(datastore_path[0])
            exit_status, output = ssh_client.run_command(command)
            ssh_client.close()
            files_in_datastore = output.splitlines() if exit_status == 0 else []
            for fil in files_in_datastore:
                if fil not in vm_registered_files:
                    file_type = 'UNKNOWN'
                    number_of_files = 0
                    command = 'test -d ~/{}/{}; echo $?'.format(datastore_path[0], fil)
                    exit_status, output = ssh_client.run_command(command)
                    ssh_client.close()
                    file_extension = re.findall(r'.*\.(\w*)', fil)
                    if file_extension:
                        file_type = file_extension[0]
                        number_of_files = 1
                    if int(output.strip()) == 0:
                        command = 'ls ~/{}/{} | wc -l'.format(datastore_path[0], fil)
                        exit_status, output = ssh_client.run_command(command)
                        number_of_files = output.strip()
                        command = 'find ~/{}/{} -name "*.vmx" | wc -l'.format(
                            datastore_path[0], fil)
                        vmx_status, vmx_output = ssh_client.run_command(command)
                        command = 'find ~/{}/{} -name "*.vmtx" | wc -l'.format(
                            datastore_path[0], fil)
                        vmtx_status, vmtx_output = ssh_client.run_command(command)
                        command = 'find ~/{}/{} -name "*.vmdk" | wc -l'.format(
                            datastore_path[0], fil)
                        vmdk_status, vmdk_output = ssh_client.run_command(command)

                        ssh_client.close()
                        if int(vmx_output.strip()) > 0:
                            file_type = 'VirtualMachine'
                        elif int(vmtx_output.strip()) > 0:
                            file_type = 'Template'
                        elif int(vmdk_output.strip()) > 0:
                            file_type = 'VMDK'
                            # delete_this = '~/' + datastore_path[0] + fil
                            # command = 'rm -rf {}'.format(delete_this)
                            # exit_status, output = ssh_client.run_command(command)
                            # logger.info(output)

                    file_path = '~/' + datastore_path[0] + fil
                    if file_path not in unregistered_files:
                        unregistered_files.append(file_path)
                        print('{}\t\t{}\t\t{}\t\t{}'.format(
                            hostname[0], file_path, file_type, number_of_files))

    except Exception as e:
        logger.error(e)
        return False


def get_registered_vm_files(provider_key):
    try:
        print("{} processing all the registered files..".format(provider_key))
        vm_registered_files = defaultdict(set)
        provider = get_mgmt(provider_key)
        for vm_name in provider.list_vm():
            try:
                vm_file_path = provider.get_vm_config_files_path(vm_name)
                vm_directory_name = re.findall(r'\s(.*)/\w*', vm_file_path)
                vm_registered_files[vm_directory_name[0]] = vm_name
            except Exception as e:
                logger.error(e)
                logger.error('Failed to get creation/boot time for {} on {}'.format(
                    vm_name, provider_key))
                continue
        print("\n**************************REGISTERED FILES ON {}***********************\n".format(
            provider_key))
        for k, v in vm_registered_files.items():
            print('FILE_NAME: {}\nVM_NAME: {}\n'.format(k, v))
        return vm_registered_files
    except Exception as ex:
            # Print out the error message too because logs in the job get deleted
        print('{} failed ({}: {})'.format(provider_key, type(ex).__name__, str(ex)))
        logger.error('failed to process vms from provider {}'.format(provider_key))
        logger.exception(ex)


def get_datastores_per_host(provider_key):
    print('{} processing to get datastores per host'.format(provider_key))
    try:
        provider = get_mgmt(provider_key)

        vm_registered_files = get_registered_vm_files(provider_key)
        hosts = provider.list_host()
        host_datastore_url = {host: provider.list_host_datastore_url(host) for host in hosts}
        unregistered_files = []

        print("\n*********************UNREGISTERED FILES ON: {}**********************\n".format(
            provider_key))
        print('HOST_NAME\t\tFILE_PATH\t\tTEMPLATE_VM_ISO\t\tNUMBER_OF_FILES\n')
        for host in host_datastore_url:
            try:
                list_orphaned_files_per_host(host, host_datastore_url[host],
                                             provider_key, vm_registered_files,
                                             unregistered_files)
            except Exception as e:
                logger.error(e)
                continue

    except Exception as ex:
            # Print out the error message too because logs in the job get deleted
        print('{} failed ({}: {})'.format(provider_key, type(ex).__name__, str(ex)))
        logger.error('failed to process vms from provider {}'.format(provider_key))
        logger.exception(ex)


def get_orphaned_vmware_files(provider=None):
    providers = [provider] if provider else list_provider_keys("virtualcenter")

    for provider_key in providers:
        # we can add thread here
        get_datastores_per_host(provider_key)


if __name__ == "__main__":
    args = parse_cmd_line()
    sys.exit(get_orphaned_vmware_files(args.provider))
