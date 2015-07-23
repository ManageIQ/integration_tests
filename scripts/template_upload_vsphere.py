#!/usr/bin/env python2

"""This script takes various parameters specified in
cfme_data['template_upload']['template_upload_vsphere'] and/or by command-line arguments.
Parameters specified by command-line have higher priority, and override data in cfme_data.

This script is designed to run either as a standalone vsphere template uploader, or it can be used
together with template_upload_all script. This is why all the function calls, which would
normally be placed in main function, are located in function run(**kwargs).
"""

import argparse
import subprocess
import sys

# from psphere.client import Client
from psphere.managedobjects import VirtualMachine, ClusterComputeResource, HostSystem, Datacenter

from utils.conf import cfme_data
from utils.conf import credentials
from utils.mgmt_system import VMWareSystem
from utils.wait import wait_for

# ovftool sometimes refuses to cooperate. We can try it multiple times to be sure.
NUM_OF_TRIES_OVFTOOL = 5


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--image_url', metavar='URL', dest="image_url",
                        help="URL of OVA", default=None)
    parser.add_argument('--template_name', dest="template_name",
                        help="Override/Provide name of template", default=None)
    parser.add_argument('--datastore', dest="datastore",
                        help="Datastore name", default=None)
    parser.add_argument('--provider', dest="provider",
                        help="Specify a vCenter connection", default=None)
    parser.add_argument('--no_template', dest='template', action='store_false',
                        help="Do not templateize the OVA", default=None)
    parser.add_argument('--no_upload', dest='upload', action='store_false',
                        help="Do not upload the new OVA", default=None)
    parser.add_argument('--no_disk', dest='disk', action='store_false',
                        help="Do not add a second disk to OVA", default=None)
    parser.add_argument('--cluster', dest="cluster",
                        help="Specify a cluster", default=None)
    parser.add_argument('--datacenter', dest="datacenter",
                        help="Specify a datacenter", default=None)
    parser.add_argument('--host', dest='host',
                        help='Specify host in cluster', default=None)
    args = parser.parse_args()
    return args


def check_template_exists(client, name):
    if name in client.list_template():
        print "VSPHERE: A Machine with that name already exists"
        return True
    else:
        return False


def upload_ova(hostname, username, password, name, datastore,
               cluster, datacenter, url, host, proxy):
    cmd_args = ['ovftool']
    cmd_args.append("--datastore=%s" % datastore)
    cmd_args.append("--name=%s" % name)
    cmd_args.append("--vCloudTemplate=True")
    cmd_args.append("--overwrite")  # require when failures happen and it retries
    if proxy:
        cmd_args.append("--proxy=%s" % proxy)
    cmd_args.append(url)
    cmd_args.append("vi://%s@%s/%s/host/%s" % (username, hostname, datacenter, cluster))

    print "VSPHERE: Running OVFTool..."

    proc = subprocess.Popen(cmd_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    out_string = ""

    while "'yes' or 'no'" not in out_string and "Password:" not in out_string:
        out_string += proc.stdout.read(1)
        # on error jump out of the while loop to prevent infinite cycling
        if "error" in out_string.lower():
            print "VSPHERE: Upload did not complete"
            return -1, out_string

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
        print output
        print error
        sys.exit(127)


def add_disk(client, name):
    print "VSPHERE: Beginning disk add..."

    backing = client.api.create("VirtualDiskFlatVer2BackingInfo")
    backing.datastore = None
    backing.diskMode = "persistent"
    backing.thinProvisioned = True

    disk = client.api.create("VirtualDisk")
    disk.backing = backing
    disk.controllerKey = 1000
    disk.key = 3000
    disk.unitNumber = 1
    disk.capacityInKB = 8388608

    disk_spec = client.api.create("VirtualDeviceConfigSpec")
    disk_spec.device = disk
    file_op = client.api.create("VirtualDeviceConfigSpecFileOperation")
    disk_spec.fileOperation = file_op.create
    operation = client.api.create("VirtualDeviceConfigSpecOperation")
    disk_spec.operation = operation.add

    devices = []
    devices.append(disk_spec)

    nc = client.api.create("VirtualMachineConfigSpec")
    nc.deviceChange = devices

    vm = VirtualMachine.get(client.api, name=name)
    task = vm.ReconfigVM_Task(spec=nc)

    def check_task(task):
        task.update()
        return task.info.state

    wait_for(check_task, [task], fail_condition="running")

    if task.info.state == "success":
        print " VSPHERE: Successfully added new disk"
        # client.api.logout()
    else:
        client.api.logout()
        print " VSPHERE: Failed to add disk"
        sys.exit(127)


def make_template(client, name):
    print "VSPHERE: Marking as Template"
    vm = VirtualMachine.get(client.api, name=name)
    try:
        vm.MarkAsTemplate()
        print " VSPHERE: Successfully templatized machine"
    except:
        print " VSPHERE: Failed to templatize machine"
        sys.exit(127)


def api_params_resolution(item_list, item_name, item_param):
    if len(item_list) == 0:
        print "VSPHERE: Cannot find %s (%s) automatically." % (item_name, item_param)
        print "Please specify it by cmd-line parameter '--%s' or in cfme_data." % item_param
        return None
    elif len(item_list) > 0:
        if len(item_list) > 1:
            print "VSPHERE: Found multiple instances of %s." % item_name
        for item in item_list:
            if hasattr(item, 'summary'):
                if hasattr(item.summary, 'overallStatus'):
                    if item.summary.overallStatus != 'red':
                        print "Picking %s : '%s'." % (item_name, item.name)
                        return item
                elif hasattr(item.summary, 'accessible'):
                    if item.summary.accessible is True:
                        print "Picking %s : '%s'." % (item_name, item.name)
                        return item
            elif hasattr(item, 'overallStatus'):
                if item.overallStatus != 'red':
                    print "Picking %s : '%s'." % (item_name, item.name)
                    return item
        print "VSPHERE: Found instances of %s, but all have status 'red'." % item_name
        print "Please specify %s manually." % item_name
        return None


def get_cluster(client):
    clusters = ClusterComputeResource.all(client.api)
    return api_params_resolution(clusters, 'cluster', 'cluster')


def get_host(client, name):
    hosts = HostSystem.all(client.api)
    if name is None:
        return api_params_resolution(hosts, 'host', 'host')
    else:
        for host in hosts:
            if host.name == name:
                return host
        print "VSPHERE: Could not find specified host '%s'" % name


def get_datastore(client, host):
    datastores = host.datastore
    return api_params_resolution(datastores, 'datastore', 'datastore')


def get_datacenter(client):
    datacenters = Datacenter.all(client.api)
    return api_params_resolution(datacenters, 'datacenter', 'datacenter')


def check_kwargs(**kwargs):
    for key, val in kwargs.iteritems():
        if val is None:
            print "VSPHERE: please supply required parameter '%s'." % key
            sys.exit(127)


def update_params_api(client, **kwargs):
    if kwargs.get('cluster') is None:
        cluster = get_cluster(client)
        kwargs['cluster'] = cluster.name
    if kwargs.get('host') is None:
        host = get_host(client, None)
        kwargs['host'] = host.name
    if kwargs.get('datastore') is None:
        if kwargs.get('host') is None:
            host = get_host(client, kwargs.get('host'))
        datastore = get_datastore(client, host)
        kwargs['datastore'] = datastore.name
    if kwargs.get('datacenter') is None:
        datacenter = get_datacenter(client)
        kwargs['datacenter'] = datacenter.name
    return kwargs


def make_kwargs(args, **kwargs):
    args_kwargs = dict(args._get_kwargs())

    if len(kwargs) is 0:
        return args_kwargs

    template_name = kwargs.get('template_name', None)
    if template_name is None:
        template_name = cfme_data['basic_info']['appliance_template']
        kwargs.update({'template_name': template_name})

    for kkey, kval in kwargs.iteritems():
        for akey, aval in args_kwargs.iteritems():
            if aval is not None:
                if kkey == akey:
                    if kval != aval:
                        kwargs[akey] = aval

    for akey, aval in args_kwargs.iteritems():
        if akey not in kwargs.iterkeys():
            kwargs[akey] = aval

    return kwargs


def run(**kwargs):
    provider = cfme_data['management_systems'][kwargs.get('provider')]
    creds = credentials[provider['credentials']]

    hostname = provider['hostname']
    username = creds['username']
    password = creds['password']

    client = VMWareSystem(hostname, username, password)

    kwargs = update_params_api(client, **kwargs)

    name = kwargs.get('template_name', None)
    if name is None:
        name = cfme_data['basic_info']['appliance_template']

    print "VSPHERE: Template Name: %s" % name

    check_kwargs(**kwargs)

    url = kwargs.get('image_url')

    if not check_template_exists(client, name):
        if kwargs.get('upload'):
            # Wrapper for ovftool - sometimes it just won't work
            for i in range(0, NUM_OF_TRIES_OVFTOOL):
                print "VSPHERE: Trying ovftool %s..." % i
                ova_ret, ova_out = upload_ova(hostname,
                                              username,
                                              password,
                                              name,
                                              kwargs.get('datastore'),
                                              kwargs.get('cluster'),
                                              kwargs.get('datacenter'),
                                              url,
                                              kwargs.get('host'),
                                              kwargs.get('proxy'))
                if ova_ret is 0:
                    break
            if ova_ret is -1:
                print "VSPHERE: Ovftool failed to upload file."
                print ova_out
                return

        if kwargs.get('disk'):
            add_disk(client, name)
        if kwargs.get('template'):
            # make_template(client, name, hostname, username, password)
            make_template(client, name)
        client.api.logout()
    print "VSPHERE: Completed successfully"


if __name__ == "__main__":
    args = parse_cmd_line()

    kwargs = cfme_data['template_upload']['template_upload_vsphere']

    final_kwargs = make_kwargs(args, **kwargs)

    run(**final_kwargs)
