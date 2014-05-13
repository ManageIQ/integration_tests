#!/usr/bin/env python2

"""Add/activate/remove a direct_lun disk on a rhevm appliance
"""

import argparse
import sys
from utils.conf import credentials, cfme_data
from utils.ssh import SSHClient
from utils.providers import provider_factory
from utils.mgmt_system import RHEVMSystem
from ovirtsdk.xml import params


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--provider', dest='provider_name', help='provider name in cfme_data')
    parser.add_argument('--vm_name', help='the name of the VM on which to act')
    parser.add_argument('--remove', help='remove disk from vm', action="store_true")
    args = parser.parse_args()

    provider = provider_factory(args.provider_name)

    # check that we are working with a rhev provider
    if not isinstance(provider, RHEVMSystem):
        sys.exit(args.providername + " is not a RHEVM system, exiting...")

    # check that the vm exists on the rhev provider, get the ip address if so
    try:
        vm = provider.api.vms.get(args.vm_name)
        ip_addr = provider.get_ip_address(args.vm_name)
    except:
        sys.exit(args.vm_name + " vm not found on provider " + args.providername + ", exiting...")

    # check for direct lun definition on provider's cfme_data.yaml
    if 'direct_lun_name' not in cfme_data['management_systems'][args.provider_name]:
        sys.exit("direct_lun_name key not in cfme_data.yaml under provider "
            + args.providername + ", exiting...")

    # does the direct lun exist
    dlun_name = cfme_data['management_systems'][args.provider_name]['direct_lun_name']
    dlun = provider.api.disks.get(dlun_name)
    if dlun is None:
        sys.exit("Direct lun disk named " + dlun_name + " is not found on provider " +
            args.provider_name)

    # add it
    if not args.remove:
        # is the disk present and active?
        vm_disk_list = vm.get_disks().list()
        for vm_disk in vm_disk_list:
            if vm_disk.name == dlun_name:
                if vm_disk.active:
                    return
                else:
                    vm_disk.actvate()
                    return

        # if not present, add it and activate
        direct_lun = params.Disk(id=dlun.id)
        added_lun = vm.disks.add(direct_lun)
        added_lun.activate()

        # Init SSH client, run pvscan on the appliance
        ssh_kwargs = {
            'username': credentials['ssh']['username'],
            'password': credentials['ssh']['password'],
            'hostname': ip_addr
        }
        client = SSHClient(**ssh_kwargs)
        status, out = client.run_command('pvscan')

    # remove it
    else:
        vm_dlun = vm.disks.get(name=dlun_name)
        if vm_dlun is None:
            return
        else:
            detach = params.Action(detach=True)
            vm_dlun.delete(action=detach)

if __name__ == '__main__':
    sys.exit(main())
