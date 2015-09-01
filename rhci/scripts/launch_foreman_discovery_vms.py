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
from fauxfactory import gen_alpha

from utils.providers import get_mgmt

from rhci_common import save_rhci_conf, ssh_client
from utils.conf import rhci
from utils.wait import wait_for

# bunch of static stuff that we can argparse up later
provider_key = 'vsphere55'
# read vm configs from here
discovery = rhci['deployments']['basic']['fusor-installer']['discovery_vms']
# then write the created VMs out to here
fusor_kwargs = rhci['deployments']['basic']['fusor']['kwargs']
# latest iso
tpl = 'rhci-foreman-discovery-tpl-dnd'
mgmt = get_mgmt(provider_key)
api = mgmt.api


def setup_vm(cpu_count, memory, disk_size):
    # These should all be ints since they're coming from yaml,
    # but some healthy paranoia is probably warranted
    cpu_count, memory, disk_size = int(cpu_count), int(memory), int(disk_size)
    vm_name = 'rhci_test_{}'.format(gen_alpha())
    print 'Provisioning RHCI VM {} on {}'.format(vm_name, provider_key)

    mgmt.clone_vm(tpl, vm_name, power_on=False, sparse=True)
    vm = mgmt._get_vm(vm_name)

    config_spec = api.create('VirtualMachineConfigSpec')
    device_changes = []
    config_spec.deviceChange = device_changes
    extra_config = []
    config_spec.extraConfig = extra_config

    # add a thinprovisioned disk
    disk_backing = api.create("VirtualDiskFlatVer2BackingInfo")
    disk_backing.datastore = None
    disk_backing.diskMode = "persistent"
    disk_backing.thinProvisioned = True

    disk = api.create("VirtualDisk")
    disk.backing = disk_backing
    disk.controllerKey = 1000
    disk.key = 3000
    disk.unitNumber = 1
    disk.capacityInKB = disk_size * 1024 * 1024

    disk_spec = api.create("VirtualDeviceConfigSpec")
    disk_spec.device = disk
    disk_spec.fileOperation = api.create("VirtualDeviceConfigSpecFileOperation").create
    disk_spec.operation = api.create("VirtualDeviceConfigSpecOperation").add
    device_changes.append(disk_spec)

    # change the CPU count
    config_spec.numCPUs = cpu_count

    # change the memory
    config_spec.memoryMB = memory * 1024

    # enable nested virt
    extra_config.append(api.create('OptionValue', key='vhv.enable', value='TRUE'))

    # apply the custom config
    try:
        vm.ReconfigVM_Task(spec=config_spec)
    except:
        print 'failed to reconfigure VM, cleaning up'
        raise

    # don't know which device is the network adapter,
    # but it's definitely the one that has the macAddress property
    for dev in vm.config.hardware.device:
        try:
            mac_addr = dev.macAddress
        except AttributeError:
            continue
    return {'vm_name': vm_name, 'mac_addr': str(mac_addr)}

# setup the hypervisors
hypervisor_macs = []
rhci.rhevm_hypervisors = []
for __ in range(discovery.num_hypervisors):
    vm = setup_vm(**discovery.hypervisor_conf)
    rhci.vm_names.append(vm['vm_name'])
    rhci.rhevm_hypervisors.append(vm['vm_name'])
    hypervisor_macs.append(vm['mac_addr'])

# setup the engine
vm = setup_vm(**discovery.engine_conf)
rhci.vm_names.append(vm['vm_name'])
rhci.rhevm_engine = vm['vm_name']
engine_mac = vm['mac_addr']

# write their macs so we can use them in the fusor step
fusor_kwargs['rhevh_macs'] = hypervisor_macs
fusor_kwargs['rhevm_mac'] = engine_mac
save_rhci_conf()

print 'Waiting for PXE setup to complete on the master'
client = ssh_client()


def pxe_ready_wait():
    res = client.run_command('test -f /var/lib/tftpboot/pxelinux.cfg/default')
    client.close()
    # return True if the file exists
    return res.rc == 0

wait_for(pxe_ready_wait, num_sec=600)

print 'Starting VMs into foreman discovery mode'


def start(vm_name):
    mgmt.start_vm(vm_name)
    print '{} started'.format(vm_name)

start(rhci.rhevm_engine)
for vm_name in rhci.rhevm_hypervisors:
    start(vm_name)
