#!/usr/bin/env python2

"""This script takes various parameters specified in
cfme_data['template_upload']['template_upload_rhevm'] and/or by command-line arguments.
Parameters specified by command-line have higher priority, and override data in cfme_data.

This script is designed to run either as a standalone rhevm template uploader, or it can be used
together with template_upload_all script. This is why all the function calls, which would
normally be placed in main function, are located in function run(**kwargs).
"""
import subprocess

import argparse
import fauxfactory
import sys
from threading import Lock, Thread

from cfme.utils import net, trackerbot
from cfme.utils.conf import cfme_data, credentials
from cfme.utils.log import logger, add_stdout_handler
from cfme.utils.providers import get_mgmt, list_provider_keys
from cfme.utils.ssh import SSHClient

lock = Lock()

add_stdout_handler(logger)


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--stream', dest='stream',
                        help='stream name: downstream-##z, upstream, upstream_stable, etc',
                        default=None)
    parser.add_argument("--image_url", dest="image_url",
                        help="URL of qcow2 file to upload", default=None)
    parser.add_argument("--template_name", dest="template_name",
                        help="Name of the new template", default=None)
    parser.add_argument("--sdomain", dest="sdomain",
                        help="Storage domain for vm and disk", default=None)
    parser.add_argument("--cluster", dest="cluster",
                        help="Set cluster to operate in", default=None)
    parser.add_argument("--disk_size", dest="disk_size",
                        help="Size of the second (database) disk, in B",
                        default=None, type=int)
    parser.add_argument("--disk_format", dest="disk_format",
                        help="Format of the second (database) disk", default=None)
    parser.add_argument("--disk_interface", dest="disk_interface",
                        help="Interface of second (database) disk", default=None)
    parser.add_argument("--provider", dest="provider",
                        help="Rhevm provider (to look for in cfme_data)", default=None)
    parser.add_argument("--glance", dest="glance",
                        help="Glance server to upload images to", default='glance11-server')
    args = parser.parse_args()
    return args


def make_ssh_client(rhevip, sshname, sshpass):
    connect_kwargs = {
        'username': sshname,
        'password': sshpass,
        'hostname': rhevip
    }
    return SSHClient(**connect_kwargs)


def is_ovirt_engine_running(rhevm_ip, sshname, sshpass):
    try:
        with make_ssh_client(rhevm_ip, sshname, sshpass) as ssh_client:
            stdout = ssh_client.run_command('systemctl status ovirt-engine').output
            # fallback to sysV commands if necessary
            if 'command not found' in stdout:
                stdout = ssh_client.run_command('service ovirt-engine status').output
        return 'running' in stdout
    except Exception:
        logger.exception('RHEVM: While checking status of ovirt engine, an exception happened')
        return False


def get_qcow_name(qcowurl):
    """Returns ova filename."""
    return qcowurl.split("/")[-1]


def download_qcow(qcowurl):
    """Downloads qcow2 file from and url

    Args:
        ssh_client: :py:class:`utils.ssh.SSHClient` instance
        qcowurl: URL of ova file
    """
    rc = subprocess.call(
        ['curl', '-O', qcowurl])
    if rc == 0:
        print('Successfully downloaded qcow2 file')
    else:
        print('There was an error while downloading qcow2 file')
        sys.exit(127)


def add_glance(mgmt, provider, glance_server):
    provider_dict = cfme_data['template_upload'][glance_server]
    creds_key = provider_dict['credentials']
    try:
        if mgmt.does_glance_server_exist(glance_server):
            logger.info("RHEVM:%r Warning: Found a Glance provider with this name (%r).",
                    provider, glance_server)
            logger.info("RHEVM:%r Skipping this step, attempting to continue", provider)
            return
        mgmt.add_glance_server(
            name=glance_server,
            description=glance_server,
            url=provider_dict['url'],
            requires_authentication=True,
            authentication_url=provider_dict['auth_url'],
            username=credentials[creds_key]['username'],
            password=credentials[creds_key]['password'],
            tenant_name=credentials[creds_key]['tenant']
        )
        logger.info('RHV:%s Attached Glance provider %s', provider, glance_server)
    except Exception:
        logger.exception("RHV:%r add_glance failed:", provider)
        sys.exit(127)


def import_template_from_glance(mgmt, sdomain, cluster, temp_template_name, glance_server, provider,
                                template_name):
    try:
        if mgmt.does_template_exist(temp_template_name):
            logger.info("RHEVM:%r Warning: found another template with this name.", provider)
            logger.info("RHEVM:%r Skipping this step, attempting to continue...", provider)
            return
        mgmt.import_glance_image(sdomain, cluster, temp_template_name, glance_server, template_name)
        logger.info("RHEVM:%r Successfully imported template from Glance", provider)
    except Exception:
        logger.exception("RHEVM:%r import_template_from_glance() failed:", provider)
        sys.exit(127)


def make_vm_from_template(mgmt, stream, cfme_data, cluster, temp_template_name,
        temp_vm_name, provider, mgmt_network=None):
    """Makes temporary VM from imported template. This template will be later deleted.
       It's used to add a new disk and to convert back to template.

    Args:
        mgmt: A ``RHEVMSystem`` instance from wrapanapi.
        cluster: Cluster to save the temporary VM on.
        mgmt_network: management network on RHEVM box, its 'ovirtmgmt' by default on rhv4.0 and
        'rhevm' on older RHEVM versions.
        temp_template_name: temporary template name created from ova
        temp_vm_name: temporary vm name to be created.
        provider: provider_key
    """
    cores = cfme_data['template_upload']['hardware'][stream]['cores']
    sockets = cfme_data['template_upload']['hardware'][stream]['sockets']
    vm_memory = cfme_data['template_upload']['hardware'][stream]['memory'] * 1024 * 1024 * 1024

    try:
        if mgmt.does_vm_exist(temp_vm_name):
            logger.info("RHEVM:%r Warning: found another VM with this name (%r).",
                        provider, temp_vm_name)
            logger.info("RHEVM:%r Skipping this step, attempting to continue...", provider)
            return

        mgmt.deploy_template(
            temp_template_name,
            vm_name=temp_vm_name,
            cluster=cluster,
            cpu=cores,
            sockets=sockets,
            ram=vm_memory
        )

        if mgmt_network:
            mgmt.update_vm_nic(temp_vm_name, mgmt_network)
        # check, if the vm is really there
        if not mgmt.does_vm_exist(temp_vm_name):
            logger.error("RHEVM:%r temp VM could not be provisioned", provider)
            sys.exit(127)
        logger.info("RHEVM:%r successfully provisioned temp vm", provider)
    except Exception:
        logger.exception("RHEVM:%r Make_temp_vm_from_template failed:", provider)


def add_disk_to_vm(mgmt, sdomain, disk_size, disk_format, disk_interface, temp_vm_name,
                   provider):
    """Adds second disk to a temporary VM.

    Args:
        mgmt: API to chosen RHEVM provider.
        sdomain: Storage domain to save new disk onto.
        disk_size: Size of the new disk (in B).
        disk_format: Format of the new disk.
        disk_interface: Interface of the new disk.
    """
    try:
        if mgmt.get_vm_disks_count(temp_vm_name) > 1:
            logger.info("RHEVM:%r Warning: found more than one disk in existing VM (%r).",
                    provider, temp_vm_name)
            logger.info("RHEVM:%r Skipping this step, attempting to continue...", provider)
            return
        mgmt.add_disk_to_vm(
            temp_vm_name,
            storage_domain=sdomain,
            size=disk_size,
            interface=disk_interface,
            format=disk_format
        )
        # check, if there are two disks
        if mgmt.get_vm_disks_count(temp_vm_name) < 2:
            logger.error("RHEVM:%r Disk failed to add", provider)
            sys.exit(127)
        logger.info("RHEVM:%r Successfully added disk", provider)
    except Exception:
        logger.exception("RHEVM:%r add_disk_to_temp_vm failed:", provider)


def templatize_vm(mgmt, template_name, cluster, temp_vm_name, provider):
    """Templatizes temporary VM. Result is template with two disks.

    Args:
        mgmt: A ``RHEVMSystem`` instance from wrapanapi.
        template_name: Name of the final template.
        cluster: Cluster to save the final template onto.
    """
    try:
        if mgmt.does_template_exist(template_name):
            logger.info("RHEVM:%r Warning: found finished template with this name (%r).",
                    provider, template_name)
            logger.info("RHEVM:%r Skipping this step, attempting to continue", provider)
            return
        mgmt.mark_as_template(
            temp_vm_name,
            temporary_name=template_name,
            cluster=cluster,
            delete=False
        )
        # check, if template is really there
        if not mgmt.does_template_exist(template_name):
            logger.error("RHEVM:%r templatizing temporary VM failed", provider)
            sys.exit(127)
        logger.info("RHEVM:%r successfully templatized the temporary VM", provider)
    except Exception:
        logger.exception("RHEVM:%r templatizing temporary VM failed", provider)


def cleanup(mgmt, qcowname, provider, temp_template_name, temp_vm_name):
    """Cleans up all the mess that the previous functions left behind.

    Args:
        mgmt: A ``RHEVMSystem`` instance from wrapanapi.
    """
    try:
        logger.info("RHEVM:%r Deleting the  .qcow2 file...", provider)
        rc = subprocess.call(
            ['rm', qcowname])
        if rc != 0:
            print('Failure deleting qcow2 file')

        logger.info("RHEVM:%r Deleting the temp_vm on sdomain...", provider)
        mgmt.delete_vm(temp_vm_name)

        logger.info("RHEVM:%r Deleting the temp_template on sdomain...", provider)
        mgmt.delete_template(temp_template_name)

    except Exception:
        logger.exception("RHEVM:%r Exception occurred in cleanup method:", provider)
        return False


def api_params_resolution(item_list, item_name, item_param):
    """Picks and prints info about parameter obtained by api call.

    Args:
        item_list: List of possible candidates to pick from.
        item_name: Name of parameter obtained by api call.
        item_param: Name of parameter representing data in the script.
    """
    if len(item_list) == 0:
        logger.info("RHEVM: Cannot find %r (%r) automatically.", item_name, item_param)
        logger.info("Please specify it by cmd-line parameter '--%r' or in cfme_data.", item_param)
        return None
    elif len(item_list) > 1:
        logger.info("RHEVM: Found multiple instances of %r. Picking '%r'.", item_name, item_list[0])
    else:
        logger.info("RHEVM: Found %r '%r'.", item_name, item_list[0])

    return item_list[0]


def get_sdomain(mgmt):
    """Discovers suitable storage domain automatically.

    Args:
        mgmt: A ``RHEVMSystem`` instance from wrapanapi.
    """
    return api_params_resolution(mgmt.list_datastore(), 'storage domain', 'sdomain')


def get_cluster(mgmt):
    """Discovers suitable cluster automatically.

    Args:
        mgmt: A ``RHEVMSystem`` instance from wrapanapi.
    """
    return api_params_resolution(mgmt.list_cluster(), 'cluster', 'cluster')


def check_kwargs(**kwargs):
    for key, val in kwargs.items():
        if val is None:
            logger.error("RHEVM: please supply required parameter '%r'.", key)
            sys.exit(127)


def update_params_api(mgmt, **kwargs):
    """Updates parameters with ones determined from api call.

    Args:
        mgmt: A ``RHEVMSystem`` instance from wrapanapi.
        kwargs: Kwargs generated from cfme_data['template_upload']['template_upload_rhevm']
    """
    if kwargs.get('sdomain') is None:
        kwargs['sdomain'] = get_sdomain(mgmt)
    if kwargs.get('cluster') is None:
        kwargs['cluster'] = get_cluster(mgmt)

    return kwargs


def make_kwargs(args, cfme_data, **kwargs):
    """Assembles all the parameters in case of running as a standalone script.
       Makes sure, that the parameters given by command-line arguments have higher priority.
       Makes sure, that all the needed parameters have proper values.

    Args:
        args: Arguments given from command-line.
        cfme_data: Data in cfme_data.yaml
        kwargs: Kwargs generated from cfme_data['template_upload']['template_upload_rhevm']
    """
    args_kwargs = dict(args._get_kwargs())

    if len(kwargs) is 0:
        return args_kwargs

    template_name = kwargs.get('template_name')
    if template_name is None:
        template_name = cfme_data['basic_info']['appliance_template']
        kwargs.update({'template_name': template_name})

    for kkey, kval in kwargs.items():
        for akey, aval in args_kwargs.items():
            if aval is not None:
                if kkey == akey:
                    if kval != aval:
                        kwargs[akey] = aval

    for akey, aval in args_kwargs.items():
        if akey not in kwargs:
            kwargs[akey] = aval

    return kwargs


def make_kwargs_rhevm(cfmeqe_data, provider):
    data = cfmeqe_data['management_systems'][provider]
    temp_up = cfme_data['template_upload']['template_upload_rhevm']

    sdomain = data['template_upload'].get('sdomain')
    cluster = data['template_upload'].get('cluster')
    mgmt_network = data['template_upload'].get('management_network')
    disk_size = temp_up.get('disk_size')
    disk_format = temp_up.get('disk_format')
    disk_interface = temp_up.get('disk_interface')

    kwargs = {'provider': provider}
    if sdomain:
        kwargs['sdomain'] = sdomain
    if cluster:
        kwargs['cluster'] = cluster
    if disk_size:
        kwargs['disk_size'] = disk_size
    if disk_format:
        kwargs['disk_format'] = disk_format
    if disk_interface:
        kwargs['disk_interface'] = disk_interface
    if mgmt_network:
        kwargs['mgmt_network'] = mgmt_network

    return kwargs


def upload_template(rhevip, sshname, sshpass, username, password,
                    provider, image_url, template_name, provider_data, stream, glance):
    try:
        logger.info("RHEVM:%r Template %r upload started", provider, template_name)
        if provider_data:
            kwargs = make_kwargs_rhevm(provider_data, provider)
            providers = provider_data['management_systems']
            mgmt = get_mgmt(kwargs.get('provider'), providers=providers)
        else:
            kwargs = make_kwargs_rhevm(cfme_data, provider)
            mgmt = get_mgmt(kwargs.get('provider'))
        kwargs['image_url'] = image_url
        kwargs['template_name'] = template_name
        qcowname = get_qcow_name(image_url)
        temp_template_name = ('auto-tmp-{}-'.format(
            fauxfactory.gen_alphanumeric(8))) + template_name
        temp_vm_name = ('auto-vm-{}-'.format(
            fauxfactory.gen_alphanumeric(8))) + template_name
        if template_name is None:
            template_name = cfme_data['basic_info']['appliance_template']

        kwargs = update_params_api(mgmt, **kwargs)
        check_kwargs(**kwargs)

        if mgmt.does_template_exist(template_name):
            logger.info("RHEVM:%r Found finished template with name %r.", provider, template_name)
            logger.info("RHEVM:%r The script will now end.", provider)
            return True

        logger.info("RHEVM:%r Downloading .qcow2 file...", provider)
        download_qcow(kwargs.get('image_url'))
        try:
            logger.info("RHEVM:%r Uploading template to Glance", provider)
            glance_args = {'image': qcowname, 'image_name_in_glance': template_name,
                'provider': glance, 'disk_format': 'qcow2'}
            getattr(__import__('image_upload_glance'), "run")(**glance_args)

            logger.info("RHEVM:%r Adding Glance", provider)
            add_glance(mgmt, provider, glance)

            logger.info("RHEVM:%r Importing new template to data domain", provider)
            import_template_from_glance(mgmt, kwargs.get('sdomain'), kwargs.get('cluster'),
                temp_template_name, glance, provider, template_name)

            logger.info("RHEVM:%r Making a temporary VM from new template", provider)
            make_vm_from_template(mgmt, stream, cfme_data, kwargs.get('cluster'),
                temp_template_name, temp_vm_name, provider, mgmt_network=kwargs.get('mgmt_network'))

            logger.info("RHEVM:%r Adding disk to created VM", provider)
            add_disk_to_vm(mgmt, kwargs.get('sdomain'), kwargs.get('disk_size'),
                kwargs.get('disk_format'), kwargs.get('disk_interface'),
                temp_vm_name, provider)

            logger.info("RHEVM:%r Templatizing VM", provider)
            templatize_vm(mgmt, template_name, kwargs.get('cluster'), temp_vm_name, provider)

            if not provider_data:
                logger.info("RHEVM:%r Add template %r to trackerbot", provider, template_name)
                trackerbot.trackerbot_add_provider_template(stream, provider, template_name)
        finally:
            cleanup(mgmt, qcowname, provider, temp_template_name, temp_vm_name)
            mgmt.disconnect()
            logger.info("RHEVM:%r Template %r upload Ended", provider, template_name)
        if provider_data and mgmt.does_template_exist(template_name):
            logger.info("RHEVM:%r Deploying Template %r", provider, template_name)
            vm_name = 'test_{}_{}'.format(template_name, fauxfactory.gen_alphanumeric(8))
            deploy_args = {'provider': provider, 'vm_name': vm_name,
                           'template': template_name, 'deploy': True}
            getattr(__import__('clone_template'), "main")(**deploy_args)
        logger.info("RHEVM:%r Template %r upload Ended", provider, template_name)
    except Exception:
        logger.exception("RHEVM:%r Template %r upload exception", provider, template_name)
        return False


def run(**kwargs):
    """Calls all the functions needed to upload new template to RHEVM.
       This is called either by template_upload_all script, or by main function.

    Args:
        **kwargs: Kwargs generated from cfme_data['template_upload']['template_upload_rhevm'].
    """
    thread_queue = []
    valid_providers = []

    providers = list_provider_keys("rhevm")
    if kwargs.get('provider_data'):
        mgmt_sys = providers = kwargs['provider_data']['management_systems']
    for provider in providers:
        if kwargs.get('provider_data'):
            if mgmt_sys[provider]['type'] != 'rhevm':
                continue
            sshname = mgmt_sys[provider]['sshname']
            sshpass = mgmt_sys[provider]['sshpass']
            rhevip = mgmt_sys[provider]['ipaddress']
        else:
            mgmt_sys = cfme_data['management_systems']
            ssh_rhevm_creds = mgmt_sys[provider]['ssh_creds']
            sshname = credentials[ssh_rhevm_creds]['username']
            sshpass = credentials[ssh_rhevm_creds]['password']
            rhevip = mgmt_sys[provider]['ipaddress']

        if (mgmt_sys[provider].get('template_upload') and
                mgmt_sys[provider]['template_upload'].get('block_upload')):
            # Providers template_upload section indicates upload should not happen on this provider
            continue

        logger.info("RHEVM:%r verifying provider's state before template upload", provider)
        if not net.is_pingable(rhevip):
            continue
        elif not is_ovirt_engine_running(rhevip, sshname, sshpass):
            logger.info('RHEVM:%r ovirt-engine service not running..', provider)
            continue
        valid_providers.append(provider)

    for provider in valid_providers:
        if kwargs.get('provider_data'):
            sshname = mgmt_sys[provider]['sshname']
            sshpass = mgmt_sys[provider]['sshpass']
            username = mgmt_sys[provider]['username']
            password = mgmt_sys[provider]['password']
        else:
            ssh_rhevm_creds = mgmt_sys[provider]['ssh_creds']
            sshname = credentials[ssh_rhevm_creds]['username']
            sshpass = credentials[ssh_rhevm_creds]['password']
            rhevm_credentials = mgmt_sys[provider]['credentials']
            username = credentials[rhevm_credentials]['username']
            password = credentials[rhevm_credentials]['password']
        rhevip = mgmt_sys[provider]['ipaddress']
        thread = Thread(target=upload_template,
                        args=(rhevip, sshname, sshpass, username, password, provider,
                              kwargs.get('image_url'), kwargs.get('template_name'),
                              kwargs.get('provider_data'), kwargs['stream'],
                              kwargs['glance']))
        thread.daemon = True
        thread_queue.append(thread)
        thread.start()

    for thread in thread_queue:
        thread.join()


if __name__ == "__main__":
    args = parse_cmd_line()

    kwargs = cfme_data['template_upload']['template_upload_rhevm']

    final_kwargs = make_kwargs(args, cfme_data, **kwargs)

    run(**final_kwargs)
