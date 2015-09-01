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

from utils.conf import cfme_data, rhci, credentials_rhci
from utils.providers import get_mgmt
from utils.wait import TimedOutError, wait_for

from rhci_common import save_rhci_conf, vnc_client

# bunch of static stuff that we can argparse/yaml/env up later
deployment_conf = rhci['deployments']['basic']['iso']
rootpw = credentials_rhci[deployment_conf['rootpw_credential']].password
provider_key = 'vsphere55'

# latest iso
# tpl = 'rhci-iso-boot-tpl-dnd'
# beta iso
tpl = 'rhci-iso-boot-tpl-beta1-dnd'
mgmt = get_mgmt(provider_key)
api = mgmt.api
vm_name = 'rhci_test_{}'.format(gen_alpha())
print 'Provisioning RHCI VM {} on {}'.format(vm_name, provider_key)

mgmt.clone_vm(tpl, vm_name, power_on=False, sparse=True)
vm = mgmt._get_vm(vm_name)

config_spec = api.create('VirtualMachineConfigSpec')
device_changes = []
config_spec.deviceChange = device_changes
extra_config = []
config_spec.extraConfig = extra_config

# XXX CD setup doesn't work, changing the file backing doesn't update the iso in vsphere
#     the temporary solution, which is terrible, is to manually create the template with
#     the correct iso attached, and not use the placeholder; psav recommends disconnecting
#     the current CD, and then reconnecting with the new backing.
# fish out the template cdrom
# for cd in vm.config.hardware.device:
#     if '(VirtualCdrom)' in str(cd):
#         break
# swap out the placeholder backing for on with the real iso
# cd_backing = api.create('VirtualCdromIsoBackingInfo')
# cd_backing.fileName = cd.backing.fileName.replace('placeholder.iso', iso)
# cd_backing.datastore = cd.backing.datastore
# cd.backing = cd_backing
#
# cd.deviceInfo.summary = cd.deviceInfo.summary.replace('placeholder.iso', iso)
# cd_spec = api.create('VirtualDeviceConfigSpec')
# cd_spec.device = cd
# cd_spec.operation = api.create('VirtualDeviceConfigSpecOperation').add
# cd_spec.fileOperation = api.create('VirtualDeviceConfigSpecFileOperation').replace
# print cd_spec
# device_changes.append(cd_spec)

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
disk.capacityInKB = 83886080

disk_spec = api.create("VirtualDeviceConfigSpec")
disk_spec.device = disk
disk_spec.fileOperation = api.create("VirtualDeviceConfigSpecFileOperation").create
disk_spec.operation = api.create("VirtualDeviceConfigSpecOperation").add
device_changes.append(disk_spec)

# Set boot to EFI -- template uses BIOS by default, so we only add the efi firmware if desired
# firmware = api.create('OptionValue', key='firmware', value='efi')
# extra_config.append(firmware)

# Config VNC endpoint -- defaults to 5990
# TODO: Inject some net_check-fu here to make sure the vnc port is available
# vnc_port = api.create('OptionValue', key='RemoteDisplay.vnc.port', value='5991')
# extra_config.append(vnc_port)

# enable nested virt, note that this is vhv.allow = TRUE on vsphere5, and isn't available before 5
extra_config.append(api.create('OptionValue', key='vhv.enable', value='TRUE'))

# apply the custom config
try:
    vm.ReconfigVM_Task(spec=config_spec)
except:
    print 'failed to reconfigure VM, cleaning up'
    raise

# Fire up the VM
mgmt.start_vm(vm_name)

# Send keystrokes to start installer (via VNC)
# TODO The actions we take and port we connect to can be conditional, based whether this
#      is efi (or not) and what VNC port we chose. For now, assume not efi and 5990

# This is terrible. Need a better way to get the host network addr from a VM
# and it should probably work on all providers that have hosts, e.g. get_vm_host_addr
host_name = vm.runtime.host.name
for host in cfme_data.management_systems[provider_key].hosts:
    if host_name in host['name']:
        break
else:
    print 'No host found :('

# sleep a little bit to let vmware start up the vnc server
sleep(45)
# very important to use the display number here, *not* the port
vnc_connect = '{}:90'.format(host['name'])

# write out the data for later steps
# vm_names is a list, as additional vms are spawned for use,
# add them here so they all get deleted in the cleanup step
save_rhci_conf(**{
    'vm_names': [vm_name],
    'provider_key': provider_key,
    'vnc_endpoint': vnc_connect,
})

# for bios, need to go down, then hit enter when the menu appears, currently the default
# for efi, the first option is missing, just hit enter. VNC has an "expect" mechanism that
# is unfortunately unreliable, so here we just get to sleep long enough for the menu to appear
# but not so long that the menu default to booting the first hard drive
vnc = vnc_client(vnc_connect)
vnc.press('down')
vnc.press('enter')

# wait for anaconda to start
sleep(120)

# fill in the root password
vnc.press('tab')  # highlight the root password config screen
vnc.press('space')  # select the root password config screen
vnc.type(rootpw)  # password
vnc.press('tab')  # select next field
vnc.type(rootpw)  # verify password
vnc.press('tab')  # select done button
vnc.press('enter')  # hit enter to select "done", which move the caret to the first field again
vnc.type(['tab', 'tab', 'enter'])  # tab back through the fields, select done again

# should now be in anaconda, need to wait for the vm to have a readable ip addr
# this means that the installer succeeded and rebooted into the installed system
# when not using vsphere, we'll need to add more checks, e.g. anaconda isn't running but gdm is
try:
    wait_result = wait_for(mgmt.get_ip_address, func_args=[vm_name],
        func_kwargs={'timeout': 5}, num_sec=3600, delay=60, fail_condition=None)
    print 'ISO deployment verification succeeded'
    # add the IP addr to the vm info
    save_rhci_conf(ip_address=str(wait_result.out))
except TimedOutError:
    print 'ISO deployment verification failed, cleaning up the VM'
    mgmt.delete_vm(vm_name)
