#!/usr/bin/env python2
"""Cleanup up resources in libvirt whose name starts with the deployment id

Requires a working libvirt connection.

LIBVIRT_DEFAULT_URI should be set, if needed, to ensure virsh is working

"""
from utils.conf import rhci

from rhci_common import virsh

# We didn't specify a pool when creating the stuff, so the default
# would have been used, which is most commonly called: "default"
volume_pool = 'default'

for vm_name in virsh('list --name').splitlines():
    if not str(vm_name).startswith(rhci.deployment_id):
        continue

    print 'Powering off VM {}'.format(vm_name)
    virsh('destroy {}'.format(vm_name))

    print 'Cleaning up VM volume for {}'.format(vm_name)
    virsh('vol-delete {} {}'.format(vm_name, volume_pool))

    print 'Removing VM {} from libvirt inventory'.format(vm_name)
    virsh('undefine {}'.format(vm_name))

print 'Done.'
