#!/usr/bin/env python2
"""Cleanup up resources in libvirt whose name starts with the deployment id

Requires a working libvirt connection.

LIBVIRT_DEFAULT_URI should be set, if needed, to ensure virsh is working

"""
from utils.conf import rhci

from rhci_common import virsh

# Shut the vms down
vms = virsh('list --name --all').splitlines()
for vm_name in vms:
    if not str(vm_name).startswith(rhci.deployment_id):
        continue

    if virsh('domstate {}'.format(vm_name)) == 'running':
        print 'Powering off VM {}'.format(vm_name)
        virsh('destroy {}'.format(vm_name))
    else:
        print 'VM {} is already shut down, skipping...'.format(vm_name)

# find and destroy the volumes
# pool-list and vol-list don't have the name --name option like list,
# so we slice the lines with [2:] to skip the headers
for pool_line in virsh('pool-list').splitlines()[2:]:
    pool_name = pool_line.split()[0]
    for vol_line in virsh('vol-list {}'.format(pool_name)).splitlines()[2:]:
        vol_name = vol_line.split()[0]
        if vol_name.startswith(rhci.deployment_id):
            print 'Deleting volume {} in pool {}'.format(vol_name, pool_name)
            virsh('vol-delete {} {}'.format(vol_name, pool_name))

# Go back through an undefine the VMs
for vm_name in vms:
    if not str(vm_name).startswith(rhci.deployment_id):
        continue

    print 'Removing VM {} from libvirt inventory'.format(vm_name)
    virsh('undefine {}'.format(vm_name))

print 'Done.'
