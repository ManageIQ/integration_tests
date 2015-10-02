#!/usr/bin/env python2
"""Cleanup up all resources in openstack whose name starts with the deployment id"""
from novaclient.exceptions import NotFound

from utils.conf import rhci
from utils.providers import get_mgmt
from utils.wait import wait_for

from rhci_common import neutron_client

mgmt = get_mgmt(rhci.provider_key)
neutron_api = neutron_client(mgmt)
deployment_id = rhci.deployment_id


def resource_delete_wait(resource):
    # resource needs to be anything with a 'get' method that will raise NotFound
    # if that resource doesn't exist. This is most things that you can get with the nova api
    try:
        resource.get()
    except NotFound:
        return True

for instance in mgmt.api.servers.list():
    if instance.name and str(instance.name).startswith(deployment_id):
        for fip in mgmt.api.floating_ips.findall(instance_id=instance.id):
            print 'Cleaning up floating IP {}'.format(fip.ip)
            fip.delete()
        print 'Cleaning up instance {}'.format(instance.name)

        instance.delete()
        wait_for(resource_delete_wait, func_args=[instance])

for network in mgmt.api.networks.list():
    if network.label and str(network.label).startswith(deployment_id):
        print 'Cleaning up network {}'.format(network.label)
        neutron_api.delete_network(network.id)
        wait_for(resource_delete_wait, func_args=[network])

for volume in mgmt.capi.volumes.list():
    if volume.display_name and str(volume.display_name).startswith(deployment_id):
        print 'Cleaning up volume {}'.format(volume.display_name)
        volume.delete()
        wait_for(resource_delete_wait, func_args=[volume])

print 'Done.'
