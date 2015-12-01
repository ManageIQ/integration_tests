#!/usr/bin/env python2
"""Provision from iso on a libvirt box

The virt-install system package needs to be installed where this script is being run.

The libvirt host must have arpwatch installed, enabled, and started. This makes it simple
to grab the IP address of started VMs. It is recommended to pass the '-e -' option to arpwatch
to suppress email spam to root.

LIBVIRT_DEFAULT_URI environment variable must be set, even if the virsh host is localhost.
In addition to making sure that virsh will work, this automation requires SSH access to the
libvirt host to look at the arpwatch DB, and it derives the SSH hostname from the
LIBVIRT_DEFAULT_URI environment variable.

Example value:
LIBVIRT_DEFAULT_URI=qemu+ssh://username@1.2.3.4/system

Note that with this example you'll need to establish host trust and passwordless authentication
with the libvirt host before running this script.

"""
import os
import sys
from time import sleep
from urlparse import urlparse
from xml.etree import ElementTree

import sarge
from fauxfactory import gen_alpha

from utils.conf import credentials, rhci
from utils.ssh import SSHClient
from utils.wait import wait_for

from rhci_common import vnc_client, save_rhci_conf, ssh_client, virsh

# bunch of static stuff that we can argparse/yaml/env up later
deployment = 'basic'
image_path = '/tmp/rhci-dvd1.iso'
# random ID - put this at the beginning of resource names to associate them with
# this build run; the cleanup script will look for this prefix and delete all associated resources
deployment_id = gen_alpha()
# can be the network name or id
public_net_config = 'bridge=br0'
private_net_config = 'bridge=br1'
libvirt_creds = credentials['libvirt-ssh']
libvirt_host = urlparse(os.environ['LIBVIRT_DEFAULT_URI']).hostname


save_rhci_conf(**{
    'deployment': deployment,
    'deployment_id': deployment_id,
    'libvirt_host': libvirt_host,
})

# derived stuff based on the parsed args above
deployment_conf = rhci['deployments'][deployment]['iso']
rootpw = credentials[deployment_conf['rootpw_credential']].password
image_url = rhci['iso_urls'][deployment_conf['build']]['RHCI']
vm_name = '{}-fusor'.format(deployment_id)
vnc_password = 'rhci'
libvirt_storage_pool = rhci['libvirt_storage_pool'] or 'default'

# SSH into libvirt host and wget the RHCI ISO
libvirt_ssh_client = SSHClient(hostname=libvirt_host, **libvirt_creds)
print 'Downloading RHCI ISO ({}) to libvirt host...'.format(deployment_conf['build'])
cmd = "wget -q {} -O {}".format(image_url, image_path)
res = libvirt_ssh_client.run_command(cmd)
if res.rc != 0:
    print "Error when downloading ISO from URL: {}".format(image_url)
    print "{}".format(res.output.strip())
    print "Failed to download RHCI ISO, stopping."

    sys.exit(1)

# virt-install the ISO we just downloaded
print 'Provisioning RHCI VM {} via libvirt'.format(vm_name)

shell_args = {
    'vm_name': vm_name,
    'memory': 12288,
    'cpus': 4,
    'libvirt_pool': libvirt_storage_pool,
    'disk_size': 100,
    'public_net_config': public_net_config,
    'private_net_config': private_net_config,
    'image_path': image_path,
    'vnc_password': vnc_password
}
cmd = sarge.shell_format('virt-install'
    ' -n {vm_name}'
    ' --os-variant=rhel7'
    ' --ram {memory}'
    ' --vcpus {cpus}'
    ' --disk bus="virtio,pool={libvirt_pool},size={disk_size}"'
    ' --cdrom {image_path}'
    ' --network {public_net_config}'
    ' --network {private_net_config}'
    ' --boot "hd,cdrom"'
    ' --graphics "vnc,listen=0.0.0.0,password={vnc_password}"'
    ' --noautoconsole',
    **shell_args)

# this will block while virt-install runs
proc = sarge.capture_both(cmd)
if proc.returncode != 0:
    print >>sys.stderr, 'virt-install failed'
    print >>sys.stderr, proc.stderr.read()
    sys.exit(1)

wait_for(lambda: virsh('domstate {}'.format(vm_name)) == 'running')
vnc_display = virsh('vncdisplay {}'.format(vm_name))
# the display that virsh gives us includes the leading colon, but not the hostname
vnc_connect = '{}{}'.format(libvirt_host, vnc_display)

# sleep a bit to let the PXE menu load up
sleep(15)

# need to go down, then hit enter when the menu appears
# yup. I made a selenium-based VNC driver for novnc. Please please please find a better way.
vnc = vnc_client(vnc_connect, password=vnc_password)
print 'libvirt VNC connections may not work correctly if shared'
print 'connecting to this display may break the automation'
vnc.press('down')
vnc.press('enter')

# wait for anaconda to start
sleep(60)

# fill in the root password

vnc.press('tab')  # highlight the root password config screen
vnc.press('space')  # select the root password config screen
vnc.type(rootpw)  # password
vnc.press('tab')  # select next field
vnc.type(rootpw)  # verify password
vnc.press('tab')  # select done button
vnc.press('enter')  # hit enter to select "done", which move the caret to the first field again
vnc.type(['tab', 'tab', 'enter'])  # tab back through the fields, select done again

# pull the mac from the first (public) interface
vm_xml = virsh('dumpxml {}'.format(vm_name))
vm_xml_tree = ElementTree.fromstring(vm_xml)
mac_addr = vm_xml_tree.find(".//interface/mac").attrib['address']

# now it gets a little silly...SSH into the libvirt host, and watch the arp table
# for this mac to appear, then grab the associated ip addr if/when it does
# libvirt_ssh_client = SSHClient(hostname=libvirt_host, **libvirt_creds)

# The install takes 10-15 minutes, and reboots when done. libvirt sees the reboot, and
# (sometimes) shuts down so wait 20 minutes for the vm to shut down,
# then start it back up if needed
print 'Waiting for install to complete'
sleep(1200)

# arpwatch stores mac addrs without leading zeros for each octet,
# so we need to do a quick conversion to get its format right
# specifically, split the mac on colons, and then format the hex digits as ints, which strips
# leading zeros (and presumably works in ways I haven't thought of to match arpwatch's format
aw_mac = ':'.join('{:x}'.format(int(x, 16)) for x in mac_addr.split(':'))


def find_ip_addr():
    if virsh('domstate {}'.format(vm_name)) != 'running':
        virsh('start {}'.format(vm_name))
    cmd = "cat /var/lib/arpwatch/arp.dat | grep -i '{}' | awk '{{ print $2 }}'".format(aw_mac)
    res = libvirt_ssh_client.run_command(cmd)
    out = res.output.strip()
    if res.rc != 0 or not out or out == '0.0.0.0':
        # command failed or didn't produce useful output
        return False
    else:
        return res.output.strip()

print 'Finding IP Address for MAC {}'.format(mac_addr)
wait_res = wait_for(find_ip_addr, delay=30, num_sec=1200)
libvirt_ssh_client.close()

# If the wait failed, it raised a TimedOutError, and the script has exited. Otherwise...
ip_address = wait_res.out
print 'IP Address is {}'.format(ip_address)
save_rhci_conf(**{
    'ip_address': ip_address,
    'fusor_vm_name': vm_name
})

print 'Waiting for SSH to become available on {}'.format(ip_address)
count = 0
while count < 21:
    count += 1
    try:
        if virsh('domstate {}'.format(vm_name)) != 'running':
            print "VM not started so issuing start command..."
            virsh('start {}'.format(vm_name))
        ssh_client().run_command('true')
        ssh_client().close()
        print "SSH available, exiting..."
        count = 50
    except:
        print "SSH not available, sleeping 60 seconds to try again"
        sleep(60)
if count < 25:
    raise Exception('SSH never came available after {} minutes'.format(str(count)))
