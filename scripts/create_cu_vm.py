#!/usr/bin/env python2
"""
Create CU VMs on a given provider.
Where possible, defaults will come from cfme_data

Usage:
1.scripts/create_cu_vm.py --provider vsphere55 --vm_name cu-vm --template fedora-22-server-template
2.scripts/create_cu_vm.py --provider vsphere55 --template fedora-22-server-template

If vm_name is not passed,the script creates these 2 CU VMs: cu-9-5 and cu-24x7
"""
import argparse
import sys

from cfme.exceptions import CUCommandException
from utils.conf import cfme_data, credentials
from utils.log import logger
from utils.providers import get_mgmt
from utils.ssh import SSHClient
from utils.virtual_machines import deploy_template, _vm_cleanup


def command_run(ssh_client, command, message):
    exit_status, output = ssh_client.run_command(command)
    if exit_status != 0:
        raise CUCommandException(message)


def make_ssh_client(ip, sshname, sshpass):
    connect_kwargs = {
        'username': sshname,
        'password': sshpass,
        'hostname': ip
    }
    return SSHClient(**connect_kwargs)


def config_cu_vm(ssh_client):
    """Downloads cu scripts and sets up cron jobs using ssh_client

    Args:
        ssh_client: :py:class:`utils.ssh.SSHClient` instance
    """
    url = cfme_data['basic_info']['capandu_scripts_url']

    logger.info('Setting up cron jobs on the CU VM')

    command_run(ssh_client, "cd /etc/init.d; wget {}/cu-disk-script.sh".format(url),
        "CU: There was an error downloading disk script file")
    command_run(ssh_client, "cd /etc/init.d; wget {}/cu-network-script.sh".format(url),
        "CU: There was an error downloading network script file")
    command_run(ssh_client,
        "chmod +x /etc/init.d/cu-disk-script.sh /etc/init.d/cu-network-script.sh",
        "CU: There was an error running chmod")
    command_run(ssh_client, "cd /tmp; wget {}/crontab.in".format(url),
        "CU: There was an error downloading crontab.in")
    command_run(ssh_client, "crontab /tmp/crontab.in",
        "CU: There was an error running crontab:")
    command_run(ssh_client, "yum install -y iperf",
        "CU: There was an error installing iperf")
    command_run(ssh_client, "yum install -y pv",
        "CU: There was an error installing pv")

    # The cron jobs run at reboot.Hence,a reboot is required.
    logger.info('Rebooting vm after setting up cron jobs')
    command_run(ssh_client, "reboot &",
        "CU: There was an error running reboot")


def vm_running(provider, vm_name):
    if provider.is_vm_running(vm_name):
        logger.info("VM {} is running".format(vm_name))
    else:
        logger.error("VM is not running")
        return 10


def cu_vm(provider, vm_name, template):
    """
    Deploys CU VM
    """
    provider_dict = cfme_data['management_systems'][provider]
    datastore = provider_dict['cap_and_util']['allowed_datastores']
    resource_pool = provider_dict['cap_and_util']['resource_pool']

    deploy_template(provider, vm_name, template,
        resourcepool=resource_pool, allowed_datastores=datastore)

    prov_mgmt = get_mgmt(provider)
    vm_running(prov_mgmt, vm_name)
    ip = prov_mgmt.get_ip_address(vm_name)

    vm_ssh_creds = provider_dict['capandu_vm_creds']
    sshname = credentials[vm_ssh_creds]['username']
    sshpass = credentials[vm_ssh_creds]['password']

    # Create cron jobs to generate disk and network activity on the CU VM.
    ssh_client = make_ssh_client(ip, sshname, sshpass)
    try:
        config_cu_vm(ssh_client)
    except CUCommandException:
        _vm_cleanup(prov_mgmt, vm_name)
        raise
    vm_running(prov_mgmt, vm_name)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--provider', help='provider key in cfme_data')
    parser.add_argument('--template', help='the name of the template to clone')
    parser.add_argument('--vm_name', help='the name of the VM to create', default=None)

    args = parser.parse_args()

    try:
        if args.vm_name is None:
            cu_vm(args.provider, 'cu-24x7', args.template)
            cu_vm(args.provider, 'cu-9-5', args.template)
        else:
            cu_vm(args.provider, args.vm_name, args.template)
    except CUCommandException as e:
        print("An exception happened: {}".format(str(e)))
        sys.exit(127)

if __name__ == "__main__":
    sys.exit(main())
