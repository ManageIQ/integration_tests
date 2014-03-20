#!/usr/bin/python

import argparse
import re
import subprocess
import sys

from psphere.client import Client
from psphere.errors import ObjectNotFoundError
from psphere.managedobjects import VirtualMachine

from utils import conf
from utils.wait import wait_for

#ovftool sometimes refuses to cooperate. We can try it multiple times to be sure.
NUM_OF_TRIES_OVFTOOL = 5


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--image_url', metavar='URL', dest="image_url",
                        help="URL of OVA", required=True)
    parser.add_argument('--template_name', dest="template_name",
                        help="Override/Provide name of template")
    parser.add_argument('--datastore', dest="datastore",
                        help="Datastore name")
    parser.add_argument('--provider', dest="provider",
                        help="Specify a vCenter connection", required=True)
    parser.add_argument('--no_template', dest='template', action='store_false',
                        help="Do not templateize the OVA", default=True)
    parser.add_argument('--no_upload', dest='upload', action='store_false',
                        help="Do not upload the new OVA", default=True)
    parser.add_argument('--no_disk', dest='disk', action='store_false',
                        help="Do not add a second disk to OVA", default=True)
    parser.add_argument('--cluster', dest="cluster",
                        help="Specify a cluster")
    parser.add_argument('--datacenter', dest="datacenter",
                        help="Specify a datacenter")
    parser.add_argument('--host', dest='host',
                        help='Specify host in cluster')
    args = parser.parse_args()
    return args


def upload_ova(hostname, username, password, name, datastore,
               cluster, datacenter, url, host):
    client = Client(server=hostname, username=username, password=password)
    try:
        VirtualMachine.get(client, name=name)
        print "VSPHERE: A Machine with that name already exists"
        sys.exit(127)
    except ObjectNotFoundError:
        pass
    client.logout()

    cmd_args = ['ovftool']
    cmd_args.append("--datastore=%s" % datastore)
    cmd_args.append("--name=%s" % name)
    cmd_args.append("--vCloudTemplate=True")
    cmd_args.append(url)
    cmd_args.append("vi://%s@%s/%s/host/%s" % (username, hostname, datacenter, cluster))

    print "VSPHERE: Running OVFTool..."
    proc = subprocess.Popen(cmd_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    out_string = ""

    while "'yes' or 'no'" not in out_string and "Password:" not in out_string:
        out_string += proc.stdout.read(1)

    if "'yes' or 'no'" in out_string:
        proc.stdin.write("yes\n")
        proc.stdin.flush()
        print "VSPHERE: Added host to SSL hosts"
        out_string = ""
        while "Password:" not in out_string:
            out_string += proc.stdout.read(1)

    proc.stdin.write(password + "\n")
    output = proc.stdout.read()
    error = proc.stderr.read()

    if "successfully" in output:
        print " VSPHERE: Upload completed"
        return 0, output
    else:
        print "VSPHERE: Upload did not complete"
        return -1, "\n".join([output, error])
        #print output
        #print error
        #sys.exit(127)


def add_disk(client, name):
    print "VSPHERE: Beginning disk add..."

    backing = client.create("VirtualDiskFlatVer2BackingInfo")
    backing.datastore = None
    backing.diskMode = "persistent"
    backing.thinProvisioned = True

    disk = client.create("VirtualDisk")
    disk.backing = backing
    disk.controllerKey = 1000
    disk.key = 3000
    disk.unitNumber = 1
    disk.capacityInKB = 8388608

    disk_spec = client.create("VirtualDeviceConfigSpec")
    disk_spec.device = disk
    file_op = client.create("VirtualDeviceConfigSpecFileOperation")
    disk_spec.fileOperation = file_op.create
    operation = client.create("VirtualDeviceConfigSpecOperation")
    disk_spec.operation = operation.add

    devices = []
    devices.append(disk_spec)

    nc = client.create("VirtualMachineConfigSpec")
    nc.deviceChange = devices

    vm = VirtualMachine.get(client, name=name)
    task = vm.ReconfigVM_Task(spec=nc)

    def check_task(task):
        task.update()
        return task.info.state

    wait_for(check_task, [task], fail_condition="running")

    if task.info.state == "success":
        print " VSPHERE: Successfully added new disk"
        client.logout()
    else:
        client.logout()
        print " VSPHERE: Failed to add disk"
        sys.exit(127)


def make_template(client, name, hostname, username, password):
    print "VSPHERE: Marking as Template"
    client = Client(server=hostname, username=username, password=password)
    vm = VirtualMachine.get(client, name=name)

    try:
        vm.MarkAsTemplate()
        print " VSPHERE: Successfully templatized machine"
    except:
        print " VSPHERE: Failed to templatize machine"
        sys.exit(127)


def run(**kwargs):
    provider = conf.cfme_data['management_systems'][kwargs.get('provider')]
    creds = conf.credentials[provider['credentials']]

    hostname = provider['hostname']
    username = creds['username']
    password = creds['password']
    datastore = kwargs.get('datastore')
    cluster = kwargs.get('cluster')
    datacenter = kwargs.get('datacenter')
    host = kwargs.get('host')

    name = kwargs.get('template_name', None)
    if name is None:
        name = conf.cfme_data['basic_info']['cfme_template_name']

    url = kwargs.get('image_url')
    print "VSPHERE: Template Name: %s" % name

    if kwargs.get('upload'):
        #Wrapper for ovftool - sometimes it just won't work
        for i in range(0, NUM_OF_TRIES_OVFTOOL):
            print "VSPHERE: Trying ovftool %s..." % i
            ova_ret, ova_out = upload_ova(hostname, username, password, name, datastore,
                                          cluster, datacenter, url, host)
            if ova_ret is 0:
                break
        if ova_ret is -1:
            print "VSPHERE: Ovftool failed to upload file."
            print ova_out
            sys.exit(127)

    client = Client(server=hostname, username=username, password=password)
    if kwargs.get('disk'):
        add_disk(client, name)
    if kwargs.get('template'):
        make_template(client, name, hostname, username, password)
    client.logout()
    print "VSPHERE: Completed successfully"


if __name__ == "__main__":
    args = parse_cmd_line()

    kwargs = dict(args._get_kwargs())

    run(**kwargs)
