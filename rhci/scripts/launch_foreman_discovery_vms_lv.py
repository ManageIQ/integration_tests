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
import sarge
import sys
from xml.etree import ElementTree

from utils.conf import rhci
from utils.wait import wait_for

from rhci_common import save_rhci_conf, ssh_client, virsh

# read vm configs from here
deployment_conf = rhci['deployments'][rhci.deployment]
discovery = deployment_conf['fusor-installer']['discovery_vms']
# then write the created VMs out to here
fusor_kwargs = deployment_conf['fusor']['kwargs']
vnc_password = 'rhci'


def setup_vm(vm_suffix, cpu_count, memory, disk_size, nested=False):
    # These should all be ints since they're coming from yaml,
    # but some healthy paranoia is probably warranted
    cpu_count, memory, disk_size = int(cpu_count), int(memory), int(disk_size)
    # libvirt wants the memory in MB
    memory *= 1024
    vm_name = '{}-{}'.format(rhci.deployment_id, vm_suffix)
    # The following is mostly copied out of the deploy from iso script,
    # and should probably be generalized in rhci_common (or something)
    print 'Provisioning RHCI VM {} via libvirt'.format(vm_name)

    shell_args = {
        'vm_name': vm_name,
        'memory': memory,
        'cpus': cpu_count,
        'disk_size': disk_size,
        'private_net_config': 'bridge:br1',
        'vnc_password': vnc_password
    }
    cmd = sarge.shell_format('virt-install -n {vm_name} --os-variant=rhel7 --ram {memory} --pxe'
        ' --vcpus {cpus} --disk bus="virtio,size={disk_size}" --network {private_net_config}'
        ' --graphics "vnc,listen=0.0.0.0,password={vnc_password}" --noautoconsole', **shell_args)

    proc = sarge.capture_both(cmd)
    if proc.returncode != 0:
        print >>sys.stderr, 'virt-install failed'
        print >>sys.stderr, proc.stderr.read()
        sys.exit(1)

    wait_for(lambda: virsh('domstate {}'.format(vm_name)) == 'running')

    vm_xml = virsh('dumpxml {}'.format(vm_name))
    vm_xml_tree = ElementTree.fromstring(vm_xml)
    mac_addr = vm_xml_tree.find(".//interface/mac").attrib['address']

    return {'vm_name': vm_name, 'mac_addr': mac_addr}


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
    vm_suffix = 'hypervisor{}'.format(i)
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
