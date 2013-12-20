#!/usr/bin/python

import argparse
import re
import subprocess
import sys

from psphere.client import Client
from psphere.errors import ObjectNotFoundError
from psphere.managedobjects import VirtualMachine

from utils.conf import yamls
from utils.credentials import load_credentials
from utils.wait import wait_for


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--url', metavar='URL', dest="url",
                        help="URL of OVA", required=True)
    parser.add_argument('--name', dest="name",
                        help="Override/Provide name of template")
    parser.add_argument('--datastore', dest="datastore",
                        help="Datastore name")
    parser.add_argument('--provider', dest="provider",
                        help="Specify a vCenter connection", required=True)
    parser.add_argument('--no-template', dest='template', action='store_false',
                        help="Do not templateize the OVA", default=True)
    parser.add_argument('--no-upload', dest='upload', action='store_false',
                        help="Do not upload the new OVA", default=True)
    parser.add_argument('--no-disk', dest='disk', action='store_false',
                        help="Do not add a second disk to OVA", default=True)
    parser.add_argument('--cluster', dest="cluster",
                        help="Specify a cluster")
    parser.add_argument('--datacenter', dest="datacenter",
                        help="Specify a datacenter")
    args = parser.parse_args()
    return args


def get_vm_name(args):
    if args.name:
        name = args.name
    else:
        match = re.search("(\d\.\d-\d{4}-\d{2}-\d{2}\.\d)", args.url)
        if match is None:
            print "Could not automatically suggest a name from URL"
            sys.exit(127)
        else:
            name = "cfme-%s" % match.groups()[0]
    return name


def upload_ova(hostname, username, password, name, datastore,
               cluster, datacenter, url):
    client = Client(server=hostname, username=username, password=password)
    try:
        VirtualMachine.get(client, name=name)
        print "A Machine with that name already exists"
        sys.exit(127)
    except ObjectNotFoundError:
        pass
    client.logout()

    cmd_args = ['ovftool']
    cmd_args.append("--datastore=%s" % datastore)
    cmd_args.append("--name=%s" % name)
    cmd_args.append("--vCloudTemplate=True")
    cmd_args.append(args.url)
    cmd_args.append("vi://%s@%s/%s/host/%s" % (username, hostname, datacenter, cluster))

    print "Running OVFTool..."
    proc = subprocess.Popen(cmd_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    out_string = ""

    while "'yes' or 'no'" not in out_string and "Password:" not in out_string:
        out_string += proc.stdout.read(1)

    if "'yes' or 'no'" in out_string:
        proc.stdin.write("yes\n")
        proc.stdin.flush()
        print "Added host to SSL hosts"
        out_string = ""
        while "Password:" not in out_string:
            out_string += proc.stdout.read(1)

    proc.stdin.write(password + "\n")
    output = proc.stdout.read()
    error = proc.stderr.read()

    if "successfully" in output:
        print " Upload completed"
    else:
        print "Upload did not complete"
        print output
        print error
        sys.exit(127)


def add_disk(client, name):
    print "Beginning disk add..."

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
        print " Successfully added new disk"
        client.logout()
    else:
        client.logout()
        print " Failed to add disk"
        sys.exit(127)


def make_template(client, name):
    print "Marking as Template"
    client = Client(server=hostname, username=username, password=password)
    vm = VirtualMachine.get(client, name=name)

    try:
        vm.MarkAsTemplate()
        print " Successfully templatized machine"
    except:
        print " Failed to templatize machine"
        sys.exit(127)


if __name__ == "__main__":
    args = parse_cmd_line()

    provider = yamls.cfme_data['management_systems'][args.provider]
    creds = load_credentials()[provider['credentials']]

    hostname = provider['hostname']
    username = creds['username']
    password = creds['password']
    datastore = args.datastore or provider['datastores'][0]
    cluster = args.cluster or provider['clusters'][0]
    datacenter = args.datacenter or provider['datacenters'][0]

    name = get_vm_name(args)
    url = args.url
    print "Template Name: %s" % name

    if args.upload:
        upload_ova(hostname, username, password, name, datastore,
                   cluster, datacenter, url)

    client = Client(server=hostname, username=username, password=password)
    if args.disk:
        add_disk(client, name)
    if args.template:
        make_template(client, name)
    client.logout()
print "Completed successfully"
