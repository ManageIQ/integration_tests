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
from threading import Lock, Thread

from cfme.utils import net, trackerbot
from cfme.utils.conf import cfme_data, credentials
from cfme.utils.log import logger, add_stdout_handler
from cfme.utils.providers import list_provider_keys
from cfme.utils.ssh import SSHClient
from wrapanapi import VMWareSystem

# ovftool sometimes refuses to cooperate. We can try it multiple times to be sure.
NUM_OF_TRIES_OVFTOOL = 5

lock = Lock()

add_stdout_handler(logger)


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

    cmd_args = []
    cmd_args.append('ovftool --noSSLVerify')
    cmd_args.append("--datastore={}".format(datastore))
    cmd_args.append("--name={}".format(name))
    cmd_args.append("--vCloudTemplate=True")
    cmd_args.append("--overwrite")  # require when failures happen and it retries
    if proxy:
        cmd_args.append("--proxy={}".format(proxy))
    cmd_args.append(url)
    cmd_args.append("'vi://{}:{}@{}/{}/host/{}'".format(username, password, hostname,
                                                      datacenter, cluster))
    logger.info("VSPHERE:%r Running OVFTool", provider)

    command = ' '.join(cmd_args)
    with make_ssh_client(ovf_tool_client, default_user, default_pass) as ssh_client:
        try:
            result = ssh_client.run_command(command)[1]
        except Exception:
            logger.exception("VSPHERE:%r Exception during upload", provider)
            return False

    if "successfully" in result:
        logger.info(" VSPHERE:%r Upload completed", provider)
        return True
    else:
        logger.error("VSPHERE:%r Upload failed: %r", provider, result)
        return False


def add_disk(client, name, provider):
    logger.info("VSPHERE:%r Adding disk to %r", provider, name)

    # adding disk #1 (base disk is 0)
    result, msg = client.add_disk_to_vm(vm_name=name,
                                        capacity_in_kb=8388608,
                                        provision_type='thin')

    if result:
        logger.info('VSPHERE:%r Added disk to vm %r', provider, name)
    else:
        logger.error(" VSPHERE:%r Failure adding disk: %r", provider, msg)

    return result


def check_kwargs(**kwargs):
    for key, val in kwargs.iteritems():
        if val is None:
            logger.error("VSPHERE:%r Supply required parameter '%r'", kwargs['provider'], key)
            return False
    return True


def make_kwargs(args, **kwargs):
    args_kwargs = dict(args._get_kwargs())

    if len(kwargs) is 0:
        return args_kwargs

    template_name = kwargs.get('template_name')
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
        kwargs['cluster'] = data['template_upload'].get('cluster')
        kwargs['datacenter'] = data['template_upload'].get('datacenter')
        kwargs['host'] = data['template_upload'].get('host')
        if data['template_upload'].get('proxy'):
            kwargs['proxy'] = data['template_upload'].get('proxy')
    else:
        kwargs['cluster'] = None
        kwargs['datacenter'] = None
        kwargs['host'] = None
        kwargs['proxy'] = None
    if data.get('provisioning'):
        kwargs['datastore'] = data['provisioning'].get('datastore')
    else:
        kwargs['datastore'] = None
    upload = temp_up.get('upload')
    disk = temp_up.get('disk')
    template = temp_up.get('template')
    kwargs['ovf_tool_client'] = temp_up.get('ovf_tool_client')

    if template:
        kwargs['template'] = template
    if upload:
        kwargs['upload'] = upload
    if disk:
        kwargs['disk'] = disk

    return kwargs


def upload_template(client, hostname, username, password,
                    provider, url, name, provider_data, stream):

    try:
        if provider_data:
            kwargs = make_kwargs_vsphere(provider_data, provider)
        else:
            kwargs = make_kwargs_vsphere(cfme_data, provider)
        kwargs['ovf_tool_username'] = credentials['host_default']['username']
        kwargs['ovf_tool_password'] = credentials['host_default']['password']

        if name is None:
            name = cfme_data['basic_info']['appliance_template']

        logger.info("VSPHERE:%r Start uploading Template: %r", provider, name)
        if not check_kwargs(**kwargs):
            return False
        if name in client.list_template():
            logger.info("VSPHERE:%r template %r already exists", provider, name)
        else:
            if kwargs.get('upload'):
                # Wrapper for ovftool - sometimes it just won't work
                for i in range(0, NUM_OF_TRIES_OVFTOOL):
                    logger.info("VSPHERE:%r ovftool try #%r", provider, i)
                    upload_result = upload_ova(hostname,
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
                    if upload_result:
                        break
                else:
                    logger.error("VSPHERE:%r Ovftool failed upload after multiple tries", provider)
                    return

            if kwargs.get('disk'):
                if not add_disk(client, name, provider):
                    logger.error('"VSPHERE:%r FAILED adding disk to VM, exiting', provider)
                    return False
            if kwargs.get('template'):
                try:
                    client.mark_as_template(vm_name=name)
                    logger.info("VSPHERE:%r Successfully templatized machine", provider)
                except Exception:
                    logger.exception("VSPHERE:%r FAILED to templatize machine", provider)
                    return False
            if not provider_data:
                logger.info("VSPHERE:%r Adding template %r to trackerbot", provider, name)
                trackerbot.trackerbot_add_provider_template(stream, provider, name)

        if provider_data and name in client.list_template():
            logger.info("VSPHERE:%r Template and provider_data exist, Deploy %r", provider, name)
            vm_name = 'test_{}_{}'.format(name, fauxfactory.gen_alphanumeric(8))
            deploy_args = {'provider': provider, 'vm_name': vm_name,
                           'template': name, 'deploy': True}
            getattr(__import__('clone_template'), "main")(**deploy_args)
    except Exception:
        logger.exception('VSPHERE:%r Exception during upload_template', provider)
        return False
    finally:
        logger.info("VSPHERE:%r End uploading Template: %r", provider, name)


def run(**kwargs):

    try:
        thread_queue = []
        providers = list_provider_keys("virtualcenter")
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
                                  kwargs['provider_data'], kwargs['stream']))
            thread.daemon = True
            thread_queue.append(thread)
            thread.start()

        for thread in thread_queue:
            thread.join()
    except Exception:
        logger.exception('Exception during run method')
        return False


if __name__ == "__main__":
    args = parse_cmd_line()

    kwargs = cfme_data['template_upload']['template_upload_vsphere']

    final_kwargs = make_kwargs(args, **kwargs)

    run(**final_kwargs)
