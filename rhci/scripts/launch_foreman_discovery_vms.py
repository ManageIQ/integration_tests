#!/usr/bin/env python2
"""Launch a foreman discovery VM on vsphere55

This requires the 'rhci-foreman-discovery-tpl-dnd' template to exist. That template
doesn't need to do anything more than PXE boot on the private RHCI network
interface being used by this automation.

This will create two VMs:
    - RHEVM Hypervisor
    - RHEVM Engine

This should be enough to support the cloudforms VM, but will likely need to be
readjusted when openstack is lit up. The number of hypervisors and the VM configs
is currently hard-coded, but should be easy to customize as implemented here.

This duplicates code from the deploy_iso script. Once this is automated work should
be done to deduplicate what we can.

"""
from novaclient.utils import find_resource

from utils.conf import rhci
from utils.providers import providers_data
from utils.wait import wait_for

from rhci_common import find_best_flavor, get_mgmt, save_rhci_conf, ssh_client

# read vm configs from here
deployment_conf = rhci['deployments'][rhci.deployment]
discovery = deployment_conf['fusor-installer']['discovery_vms']
# then write the created VMs out to here
fusor_kwargs = deployment_conf['fusor']['kwargs']
# this should probably be stashed in the conf
pxe_image_name = 'PXE Booter'
mgmt = get_mgmt()
api = mgmt.api
pxe_image = find_resource(api.images, pxe_image_name)

# server zones for normal and nested virt; hypervisors need to be nested
server_zone = providers_data[rhci.provider_key].server_zone
nested_server_zone = providers_data[rhci.provider_key].nested_server_zone


def setup_vm(vm_suffix, cpu_count, memory, disk_size, nested=False):
    # These should all be ints since they're coming from yaml,
    # but some healthy paranoia is probably warranted
    cpu_count, memory, disk_size = int(cpu_count), int(memory), int(disk_size)
    flavor = find_best_flavor(api, cpu_count, memory, disk_size)
    vm_name = '{} {}'.format(rhci.deployment_id, vm_suffix)
    print 'Provisioning RHCI VM {} on {}'.format(vm_name, rhci.provider_key)

    # make a new volume based on PXE boot image
    volume_name = '{} volume'.format(vm_name)
    volume = mgmt.capi.volumes.create(name=volume_name,
        imageRef=pxe_image.id, size=disk_size)

    # needed this in the deploy iso step, should be generalized
    def volume_available_wait(volume):
        volume.get()
        return volume.status == 'available'
    wait_for(volume_available_wait, func_args=[volume], fail_condition=False)

    # rename the volume for cleanup
    # while a name was specified in the create call above, as far as I can tell
    # cinder just ignores that and defaults to the volume's id
    volume = find_resource(mgmt.capi.volumes, volume.id)
    volume.update(display_name=volume_name)
    # and, of course, we're looking to boot from this volume, so make it bootable
    volume.manager.set_bootable(volume, True)

    volumes_spec = [
        {
            'destination_type': 'volume',
            'device_name': '/dev/sda',
            'delete_on_termination': False,
            'uuid': volume.id,
            'source_type': 'volume',
            'boot_index': 0,
        }
    ]

    # attach a nic to the private net
    nics_spec = [
        {'net-id': rhci.private_net_id},
    ]

    if nested:
        zone = nested_server_zone
    else:
        zone = server_zone

    # XXX This isn't working, the volume creation is failing.
    # A bug was reported on the error I was seeing, with the workaround being to manually
    # create the volume from the image, and then boot with the source_type 'volume', instead of
    # source_type 'image'. Next up: cinder api spelunkation
    instance = api.servers.create(vm_name, None, flavor,
        availability_zone=zone, security_groups=['default'],
        block_device_mapping_v2=volumes_spec, nics=nics_spec)
    mgmt.wait_vm_running(vm_name)

    # we only added the one nic...
    mac_addr = instance.interface_list()[0].mac_addr
    return {'vm_name': vm_name, 'mac_addr': str(mac_addr)}


print 'Waiting for PXE setup to complete on the master'
client = ssh_client()


def pxe_ready_wait():
    res = client.run_command('test -f /var/lib/tftpboot/pxelinux.cfg/default')
    client.close()
    # return True if the file exists
    return res.rc == 0

wait_for(pxe_ready_wait, num_sec=600)

print 'Starting VMs into foreman discovery mode'
# setup the hypervisors
hypervisor_macs = []
rhci.rhevm_hypervisors = []
for i in range(discovery.num_hypervisors):
    vm_suffix = 'hypervisor {}'.format(i)
    vm = setup_vm(vm_suffix, nested=True, **discovery.hypervisor_conf)
    rhci.rhevm_hypervisors.append(vm['vm_name'])
    hypervisor_macs.append(vm['mac_addr'])

# setup the engine
vm = setup_vm('engine', nested=False, **discovery.engine_conf)
rhci.rhevm_engine = vm['vm_name']
engine_mac = vm['mac_addr']

# write their macs so we can use them in the fusor step
fusor_kwargs['rhevh_macs'] = hypervisor_macs
fusor_kwargs['rhevm_mac'] = engine_mac
save_rhci_conf()
