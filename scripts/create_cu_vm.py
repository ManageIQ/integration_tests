#!/usr/bin/env python3
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

from wait_for import TimedOutError
from wrapanapi import VmState

from cfme.exceptions import CUCommandException
from cfme.utils.conf import credentials
from cfme.utils.config_data import cfme_data
from cfme.utils.log import logger
from cfme.utils.ssh import SSHClient
from cfme.utils.virtual_machines import deploy_template


def command_run(ssh_client, command, message):
    result = ssh_client.run_command(command)
    if result.failed:
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


def cu_vm(provider, vm_name, template):
    """
    Deploys CU VM
    """
    provider_dict = cfme_data['management_systems'][provider]
    # TODO this key isn't in cfme qe yamls
    datastore = provider_dict['cap_and_util']['allowed_datastores']
    resource_pool = provider_dict['cap_and_util']['resource_pool']

    # TODO methods deploy_template calls don't accept resourcepool and  allowed_datastores as kwargs
    vm = deploy_template(
        provider, vm_name, template,
        resourcepool=resource_pool, allowed_datastores=datastore
    )

    vm.ensure_state(VmState.RUNNING, timeout='2m')

    ip = vm.ip
    assert vm.ip, "VM has no IP"

    # TODO this key isn't in cfme qe yamls
    vm_ssh_creds = provider_dict['capandu_vm_creds']
    sshname = credentials[vm_ssh_creds]['username']
    sshpass = credentials[vm_ssh_creds]['password']

    # Create cron jobs to generate disk and network activity on the CU VM.
    with make_ssh_client(ip, sshname, sshpass) as ssh_client:
        try:
            config_cu_vm(ssh_client)
            # Reboot so cron jobs get picked up
            vm.restart()
            vm.wait_for_state(VmState.RUNNING)
        except (CUCommandException, TimedOutError):
            vm.cleanup()
            raise

    assert vm.is_running, "VM is not running"


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
