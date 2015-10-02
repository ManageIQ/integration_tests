#!/usr/bin/env python2
"""Provision from iso on vsphere55

This requires the 'rhci-iso-boot-tpl-dnd' template to exist. That template is a basic
VM, preconfigured with the correct disk, network, and VNC config, intended to be
tweaked before instantiation with the correct iso name, at which point it shoud boot
and install.

As time goes on, we'll be getting other providers set up to support this worrkflow,
but for now it's just vsphere55.
"""
from time import sleep

from fauxfactory import gen_alpha
from novaclient.utils import find_resource

from utils.conf import credentials, rhci
from utils.wait import wait_for

from rhci_common import get_mgmt, neutron_client, openstack_vnc_console, save_rhci_conf, ssh_client

# bunch of static stuff that we can argparse/yaml/env up later
deployment = 'basic'
provider_key = 'cci7'
image_id = 'RHCI-6.0-RHEL-7-20150829.0-RHCI-x86_64'
# random ID - put this at the beginning of resource names to associate them with
# this build run; the cleanup script will look for this prefix and delete all associated resources
deployment_id = gen_alpha()
# can be the network name or id
public_net_id = 'rhci-qe-jenkins'
# need at least 12G of RAM, so the smallest flavor we can use is m1.xlarge
# like network, can be the flavor name or ID
flavor_id = 'm1.xlarge'
floating_ip_pool = '10.8.188.0/24'

save_rhci_conf(**{
    'deployment': deployment,
    'deployment_id': deployment_id,
    'provider_key': provider_key,
})

# derived stuff based on the parsed args above
deployment_conf = rhci['deployments'][deployment]['iso']
rootpw = credentials[deployment_conf['rootpw_credential']].password
mgmt = get_mgmt()
api = mgmt.api
neutron_api = neutron_client(mgmt)
vm_name = '{} anaconda'.format(deployment_id)

print 'Provisioning RHCI VM {} on {}'.format(vm_name, provider_key)

# get a ref to the public net
# can go through nova or neutron, nova returns more useful values (objects, not dicts)
public_net = find_resource(api.networks, public_net_id)

# create our private network
# private network is managed by satellite, so no subnet, no router, etc
private_net_id = '{} private'.format(deployment_id)
neutron_api.create_network({'network':
    {
        'name': '{} private'.format(deployment_id),
        'router:external': False,
        'shared': False,
        'admin_state_up': True
    }
})
private_net = find_resource(api.networks, private_net_id)

# attach a subnet to the private network, using the link local v4 space
neutron_api.create_subnet({'subnet':
    {
        'name': '{} subnet'.format(deployment_id),
        'cidr': '169.254.0.0/16',
        'enable_dhcp': False,
        'network_id': private_net.id,
        'gateway_ip': None,
        'ip_version': 4
    }
})


# set up the block dev mapping for creating the install volume, need at least 60G for fusor
# these are set to delete on terminate so we don't have to deal with volumes on cleanup
volumes_spec = [
    {
        'source_type': 'blank',
        'destination_type': 'volume',
        'volume_size': 100,
        'delete_on_termination': False
    },
]

# add the nics, eth0 is public, eth1 is private
nics_spec = [
    {'net-id': public_net.id},
    {'net-id': private_net.id},
]

# get the image and flavor
image = find_resource(api.images, image_id)
flavor = find_resource(api.flavors, flavor_id)

# write out the data for later steps
save_rhci_conf(public_net_id=public_net.id, private_net_id=private_net.id)

# actually make the thing!
anaconda_instance = api.servers.create(vm_name, image, flavor,
    availability_zone='nova', security_groups=['default'],
    block_device_mapping_v2=volumes_spec, nics=nics_spec)

# try to pull in the fancy, but private, instance status monitor, else fall back to mgmt wait
try:
    from novaclient.v2.shell import _poll_for_status
    _poll_for_status(api.servers.get, anaconda_instance.id, 'building', ['active'])
except ImportError:
    mgmt.wait_vm_running(vm_name)

# rename the volume so we can easily clean it up later, also set it bootable
instance_volume = mgmt.capi.volumes.find(display_name='{}-blank-vol'.format(anaconda_instance.id))
instance_volume.update(display_name='{} satellite volume'.format(deployment_id))
instance_volume.manager.set_bootable(instance_volume, True)

floating_ip = api.floating_ips.create(pool=floating_ip_pool)
print 'Adding floating ip {} to instance'.format(floating_ip.ip)
anaconda_instance.add_floating_ip(floating_ip.ip)

save_rhci_conf(**{
    'ip_address': floating_ip.ip
})

# sleep a bit to let the PXE menu load up
sleep(15)

# need to go down, then hit enter when the menu appears
# yup. I made a selenium-based VNC driver for novnc. Please please please find a better way.
vnc = openstack_vnc_console(vm_name)
vnc.press('Down')
vnc.press('Return')

# give anaconda a minute to start
sleep(60)

# fill in the root password
vnc.press('Tab')  # highlight the root password config screen
vnc.press('space')  # select the root password config screen
vnc.type(rootpw)  # password
vnc.press('Tab')  # select next field
vnc.type(rootpw)  # verify password
vnc.press('Tab')  # select done button
vnc.press('Return')  # hit enter to select "done", which move the caret to the first field again
vnc.type(['Tab', 'Tab', 'Return'])  # tab back through the fields, select done again

# at this point, the installer will run for a few minutes, and attempt to reboot. At that point,
# it will fail because the first hard drive is still the iso image. So, we've got to kill this
# instance, and build another that boots from the volume we just made.

# The install takes 10-15 minutes, so we'll give it 20 for some padding.
sleep(1200)
anaconda_instance.delete()


def volume_available_wait(volume):
    volume.get()
    return volume.status == 'available'

# wait for the instance volume to become available so we can attach it to a new instance
wait_for(volume_available_wait, func_args=[instance_volume], fail_condition=False)

# recreate the instance using the same settings, but no image and referencing the volume
# that was created and used during the anaconda install step

fusor_vm_name = '{} fusor'.format(deployment_id)
fusor_volumes_spec = [
    {
        'destination_type': 'volume',
        'device_name': '/dev/sda',
        'delete_on_termination': False,
        'uuid': instance_volume.id,
        'source_type': 'volume',
        'boot_index': 0,
    },
    # If you want/need swap (not sure yet...)
    # {
    #     'source_type': 'blank',
    #     'destination_type': 'local',
    #     'boot_index': -1,
    #     'delete_on_termination': True,
    #     'guest_format': 'swap',
    #     'volume_size': 6
    # }
]

fusor_instance = api.servers.create(fusor_vm_name, None, flavor,
    availability_zone='nova', security_groups=['default'],
    block_device_mapping_v2=fusor_volumes_spec, nics=nics_spec)
# wait for the vm to come back up, then reassign the floating IP
mgmt.wait_vm_running(fusor_vm_name)
anaconda_instance.add_floating_ip(floating_ip.ip)
save_rhci_conf(fusor_vm_name=fusor_vm_name)

print 'Waiting for SSH to become available on {}'.format(floating_ip.ip)


def ssh_wait():
    # ssh_client from rhci_common
    res = ssh_client().run_command('true')
    return res.rc == 0
wait_for(ssh_wait, squash_exceptions=True)
