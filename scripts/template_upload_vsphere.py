#!/usr/bin/env python2

"""This script takes various parameters specified in
cfme_data['template_upload']['template_upload_vsphere'] and/or by command-line arguments.
Parameters specified by command-line have higher priority, and override data in cfme_data.

This script is designed to run either as a standalone vsphere template uploader, or it can be used
together with template_upload_all script. This is why all the function calls, which would
normally be placed in main function, are located in function run(**kwargs).
"""

import argparse
import fauxfactory
import sys
from threading import Lock, Thread

# from psphere.client import Client
from psphere.managedobjects import VirtualMachine, ClusterComputeResource, HostSystem, Datacenter

from utils import net
from utils.conf import cfme_data
from utils.conf import credentials
from utils.providers import list_providers
from utils.ssh import SSHClient
from mgmtsystem import VMWareSystem
from utils.wait import wait_for

# ovftool sometimes refuses to cooperate. We can try it multiple times to be sure.
NUM_OF_TRIES_OVFTOOL = 5

lock = Lock()


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


def check_template_exists(client, name, provider):
    if name in client.list_template():
        print("VSPHERE:{} template {} already exists".format(provider, name))
        return True
    else:
        return False


def make_ssh_client(rhevip, sshname, sshpass):
    connect_kwargs = {
        'username': sshname,
        'password': sshpass,
        'hostname': rhevip
    }
    return SSHClient(**connect_kwargs)


def upload_ova(hostname, username, password, name, datastore,
               cluster, datacenter, url, provider, proxy,
               ovf_tool_client, default_user, default_pass):

    cmd_args = ['ovftool']
    cmd_args.append("--datastore={}".format(datastore))
    cmd_args.append("--name={}".format(name))
    cmd_args.append("--vCloudTemplate=True")
    cmd_args.append("--overwrite")  # require when failures happen and it retries
    if proxy:
        cmd_args.append("--proxy={}".format(proxy))
    cmd_args.append(url)
    cmd_args.append("vi://{}:{}@{}/{}/host/{}".format(username, password, hostname,
                                                      datacenter, cluster))
    print("VSPHERE:{} Running OVFTool...".format(provider))

    sshclient = make_ssh_client(ovf_tool_client, default_user, default_pass)
    try:
        command = ' '.join(cmd_args)
        output = sshclient.run_command(command)[1]
    except Exception as e:
        print(e)
        print("VSPHERE:{} Upload did not complete".format(provider))
        return False
    finally:
        sshclient.close()

    if "successfully" in output:
        print(" VSPHERE:{} Upload completed".format(provider))
        return 0, output
    else:
        print("VSPHERE:{} Upload did not complete".format(provider))
        print(output)
        return False


def add_disk(client, name, provider):
    print("VSPHERE:{} Beginning disk add...".format(provider))

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
        print(" VSPHERE:{} Successfully added new disk".format(provider))
    else:
        client.api.logout()
        print(" VSPHERE:{} Failed to add disk".format(provider))
        return False


def make_template(client, name, provider):
    print("VSPHERE:{} Marking as Template".format(provider))
    vm = VirtualMachine.get(client.api, name=name)
    try:
        vm.MarkAsTemplate()
        print(" VSPHERE:{} Successfully templatized machine".format(provider))
    except:
        print(" VSPHERE:{} Failed to templatize machine".format(provider))
        sys.exit(127)


def api_params_resolution(item_list, item_name, item_param):
    if len(item_list) == 0:
        print("VSPHERE: Cannot find {} ({}) automatically.".format(item_name, item_param))
        print("Please specify it by cmd-line parameter '--{}' or in cfme_data.".format(item_param))
        return None
    elif len(item_list) > 0:
        if len(item_list) > 1:
            print("VSPHERE: Found multiple instances of {}.".format(item_name))
        for item in item_list:
            if hasattr(item, 'summary'):
                if hasattr(item.summary, 'overallStatus'):
                    if item.summary.overallStatus != 'red':
                        print("Picking {} : '{}'.".format(item_name, item.name))
                        return item
                elif hasattr(item.summary, 'accessible'):
                    if item.summary.accessible is True:
                        print("Picking {} : '{}'.".format(item_name, item.name))
                        return item
            elif hasattr(item, 'overallStatus'):
                if item.overallStatus != 'red':
                    print("Picking {} : '{}'.".format(item_name, item.name))
                    return item
        print("VSPHERE: Found instances of {}, but all have status 'red'.".format(item_name))
        print("Please specify {} manually.".format(item_name))
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
        print("VSPHERE: Could not find specified host '{}'".format(name))


def get_datastore(client, host):
    datastores = host.datastore
    return api_params_resolution(datastores, 'datastore', 'datastore')


def get_datacenter(client):
    datacenters = Datacenter.all(client.api)
    return api_params_resolution(datacenters, 'datacenter', 'datacenter')


def check_kwargs(**kwargs):
    for key, val in kwargs.iteritems():
        if val is None:
            print("VSPHERE:{} please supply required parameter '{}'.".format(
                kwargs['provider'], key))
            return False
    return True


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


def make_kwargs_vsphere(cfmeqe_data, provider):
    data = cfmeqe_data['management_systems'][provider]
    temp_up = cfme_data['template_upload']['template_upload_vsphere']

    kwargs = {'provider': provider}
    if data.get('template_upload'):
        kwargs['cluster'] = data['template_upload'].get('cluster', None)
        kwargs['datacenter'] = data['template_upload'].get('datacenter', None)
        kwargs['host'] = data['template_upload'].get('host', None)
        if data['template_upload'].get('proxy', None):
            kwargs['proxy'] = data['template_upload'].get('proxy', None)
    else:
        kwargs['cluster'] = None
        kwargs['datacenter'] = None
        kwargs['host'] = None
        kwargs['proxy'] = None
    if data.get('provisioning'):
        kwargs['datastore'] = data['provisioning'].get('datastore', None)
    else:
        kwargs['datastore'] = None
    upload = temp_up.get('upload', None)
    disk = temp_up.get('disk', None)
    template = temp_up.get('template', None)
    kwargs['ovf_tool_client'] = temp_up.get('ovf_tool_client', None)

    if template:
        kwargs['template'] = template
    if upload:
        kwargs['upload'] = upload
    if disk:
        kwargs['disk'] = disk

    return kwargs


def upload_template(client, hostname, username, password,
                    provider, url, name, provider_data):

    try:
        if provider_data:
            kwargs = make_kwargs_vsphere(provider_data, provider)
        else:
            kwargs = make_kwargs_vsphere(cfme_data, provider)
        kwargs['ovf_tool_username'] = credentials['host_default']['username']
        kwargs['ovf_tool_password'] = credentials['host_default']['password']

        if name is None:
            name = cfme_data['basic_info']['appliance_template']

        print("VSPHERE:{} Start uploading Template: {}".format(provider, name))
        if not check_kwargs(**kwargs):
            return False
        if not check_template_exists(client, name, provider):
            if kwargs.get('upload'):
                # Wrapper for ovftool - sometimes it just won't work
                ova_ret, ova_out = (1, 'no output yet')
                for i in range(0, NUM_OF_TRIES_OVFTOOL):
                    print("VSPHERE:{} Trying ovftool {}...".format(provider, i))
                    ova_ret, ova_out = upload_ova(hostname,
                                                  username,
                                                  password,
                                                  name,
                                                  kwargs.get('datastore'),
                                                  kwargs.get('cluster'),
                                                  kwargs.get('datacenter'),
                                                  url,
                                                  provider,
                                                  kwargs.get('proxy'),
                                                  kwargs.get('ovf_tool_client'),
                                                  kwargs['ovf_tool_username'],
                                                  kwargs['ovf_tool_password'])
                    if ova_ret is 0:
                        break
                if ova_ret is -1:
                    print("VSPHERE:{} Ovftool failed to upload file.".format(provider))
                    print(ova_out)
                    return

            if kwargs.get('disk'):
                add_disk(client, name, provider)
            if kwargs.get('template'):
                # make_template(client, name, hostname, username, password)
                make_template(client, name, provider)

        if provider_data and check_template_exists(client, name, provider):
            print("VSPHERE:{} Deploying {}....".format(provider, name))
            vm_name = 'test_{}_{}'.format(name, fauxfactory.gen_alphanumeric(8))
            deploy_args = {'provider': provider, 'vm_name': vm_name,
                           'template': name, 'deploy': True}
            getattr(__import__('clone_template'), "main")(**deploy_args)
        client.api.logout()
    except Exception as e:
        print(e)
        return False
    finally:
        print("VSPHERE:{} End uploading Template: {}".format(provider, name))


def run(**kwargs):

    try:
        thread_queue = []
        providers = list_providers("virtualcenter")
        if kwargs['provider_data']:
            mgmt_sys = providers = kwargs['provider_data']['management_systems']
        for provider in providers:
            if kwargs['provider_data']:
                if mgmt_sys[provider]['type'] != 'virtualcenter':
                    continue
                username = mgmt_sys[provider]['username']
                password = mgmt_sys[provider]['password']
            else:
                mgmt_sys = cfme_data['management_systems']
                creds = credentials[mgmt_sys[provider]['credentials']]
                username = creds['username']
                password = creds['password']
            host_ip = mgmt_sys[provider]['ipaddress']
            hostname = mgmt_sys[provider]['hostname']
            client = VMWareSystem(hostname, username, password)

            if not net.is_pingable(host_ip):
                continue
            thread = Thread(target=upload_template,
                            args=(client, hostname, username, password, provider,
                                  kwargs.get('image_url'), kwargs.get('template_name'),
                                  kwargs['provider_data']))
            thread.daemon = True
            thread_queue.append(thread)
            thread.start()

        for thread in thread_queue:
            thread.join()
    except Exception as e:
        print(e)
        return False


if __name__ == "__main__":
    args = parse_cmd_line()

    kwargs = cfme_data['template_upload']['template_upload_vsphere']

    final_kwargs = make_kwargs(args, **kwargs)

    run(**final_kwargs)
