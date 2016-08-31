#!/usr/bin/env python2

"""This script takes various parameters specified in
cfme_data['template_upload']['template_upload_rhevm'] and/or by command-line arguments.
Parameters specified by command-line have higher priority, and override data in cfme_data.

This script is designed to run either as a standalone rhevm template uploader, or it can be used
together with template_upload_all script. This is why all the function calls, which would
normally be placed in main function, are located in function run(**kwargs).
"""

import argparse
import fauxfactory
import re
import sys
from threading import Lock, Thread

from ovirtsdk.xml import params

from utils import net, trackerbot
from utils.conf import cfme_data
from utils.conf import credentials
from utils.providers import get_mgmt, list_providers
from utils.ssh import SSHClient
from utils.wait import wait_for

lock = Lock()


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument("--image_url", dest="image_url",
                        help="URL of ova file to upload", default=None)
    parser.add_argument("--template_name", dest="template_name",
                        help="Name of the new template", default=None)
    parser.add_argument("--edomain", dest="edomain",
                        help="Export domain for the remplate", default=None)
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
        ssh_client = make_ssh_client(rhevm_ip, sshname, sshpass)
        stdout = ssh_client.run_command('service ovirt-engine status')[1]
        ssh_client.close()
        if 'running' not in stdout:
            return False
        return True
    except Exception as e:
        print(e)
        return False


def change_edomain_state(api, state, edomain, provider):
    try:
        dcs = api.datacenters.list()
        for dc in dcs:
            export_domain = dc.storagedomains.get(edomain)
            if export_domain:
                if state == 'maintenance' and export_domain.get_status().state == 'active':
                    dc.storagedomains.get(edomain).deactivate()
                elif state == 'active' and export_domain.get_status().state != 'active':
                    dc.storagedomains.get(edomain).activate()

                wait_for(is_edomain_in_state,
                        [api, state, edomain], fail_condition=False, delay=5)
                print('RHEVM:{} {} successfully set to {} state'.format(provider, edomain, state))
                return True
        return False
    except Exception as e:
        print(e)
        print("RHEVM:{} Exception occurred while changing {} state to {}".format(
            provider, edomain, state))
        return False


def is_edomain_in_state(api, state, edomain):
    dcs = api.datacenters.list()
    for dc in dcs:
        export_domain = dc.storagedomains.get(edomain)
        if export_domain:
            return export_domain.get_status().state == state
    return False


def get_ova_name(ovaurl):
    """Returns ova filename."""
    return ovaurl.split("/")[-1]


def download_ova(ssh_client, ovaurl):
    """Downloads ova file using ssh_client and url

    Args:
        ssh_client: :py:class:`utils.ssh.SSHClient` instance
        ovaurl: URL of ova file
    """
    command = 'curl -O {}'.format(ovaurl)
    exit_status, output = ssh_client.run_command(command)
    if exit_status != 0:
        print("RHEVM: There was an error while downloading ova file:")
        print(output)
        sys.exit(127)


def template_from_ova(api, username, password, rhevip, edomain, ovaname, ssh_client,
                      temp_template_name, provider):
    """Uses rhevm-image-uploader or engine-image-uploader based on rhevm-image-uploader version
       to make a template from ova file.

    Args:
        api: API for RHEVM.
        username: Username to chosen RHEVM provider.
        password: Password to chosen RHEVM provider.
        rhevip: IP of chosen RHEVM provider.
        edomain: Export domain of selected RHEVM provider.
        ovaname: Name of ova file.
        ssh_client: :py:class:`utils.ssh.SSHClient` instance
        temp_template_name: temporary template name (this template will be deleted)
    """
    if api.storagedomains.get(edomain).templates.get(temp_template_name) is not None:
        print("RHEVM:{} Warning: found another template with this name.".format(provider))
        print("RHEVM:{} Skipping this step. Attempting to continue...".format(provider))
        return
    version_cmd = 'rpm -qa| grep image-uploader'
    command = ['rhevm-image-uploader']
    status, out = ssh_client.run_command(version_cmd)
    if status == 0:
        version = re.findall(r'(\d.\d)', out)[0]
        if float(version) >= 3.6:
            command = ['engine-image-uploader']
    command.append("-u {}".format(username))
    command.append("-p {}".format(password))
    command.append("-r {}:443".format(rhevip))
    command.append("-N {}".format(temp_template_name))
    command.append("-e {}".format(edomain))
    command.append("upload {}".format(ovaname))
    command.append("-m --insecure")
    exit_status, output = ssh_client.run_command(' '.join(command))
    if exit_status != 0:
        print("RHEVM:{} There was an error while making template from ova file:".format(provider))
        print(output)
        sys.exit(127)
    print("RHEVM:{} successfully created template from ova file:".format(provider))


def import_template(api, edomain, sdomain, cluster, temp_template_name, provider):
    """Imports template from export domain to storage domain.

    Args:
        api: API to RHEVM instance.
        edomain: Export domain of selected RHEVM provider.
        sdomain: Storage domain of selected RHEVM provider.
        cluster: Cluster to save imported template on.
    """
    if api.templates.get(temp_template_name) is not None:
        print("RHEVM:{} Warning: found another template with this name.".format(provider))
        print("RHEVM:{} Skipping this step, attempting to continue...".format(provider))
        return
    actual_template = api.storagedomains.get(edomain).templates.get(temp_template_name)
    actual_storage_domain = api.storagedomains.get(sdomain)
    actual_cluster = api.clusters.get(cluster)
    import_action = params.Action(async=False, cluster=actual_cluster,
                                  storage_domain=actual_storage_domain)
    actual_template.import_template(action=import_action)
    # Check if the template is really there
    if not api.templates.get(temp_template_name):
        print("RHEVM:{} The template failed to import on data domain".format(provider))
        sys.exit(127)
    print("RHEVM:{} successfully imported template on data domain".format(provider))


def make_vm_from_template(api, cluster, temp_template_name, temp_vm_name, provider):
    """Makes temporary VM from imported template. This template will be later deleted.
       It's used to add a new disk and to convert back to template.

    Args:
        api: API to chosen RHEVM provider.
        cluster: Cluster to save the temporary VM on.
    """
    if api.vms.get(temp_vm_name) is not None:
        print("RHEVM:{} Warning: found another VM with this name.".format(provider))
        print("RHEVM:{} Skipping this step, attempting to continue...".format(provider))
        return
    actual_template = api.templates.get(temp_template_name)
    actual_cluster = api.clusters.get(cluster)
    params_vm = params.VM(name=temp_vm_name, template=actual_template, cluster=actual_cluster)
    api.vms.add(params_vm)

    # we must wait for the vm do become available
    def check_status():
        status = api.vms.get(temp_vm_name).get_status()
        if status.state != 'down':
            return False
        return True

    wait_for(check_status, fail_condition=False, delay=5)

    # check, if the vm is really there
    if not api.vms.get(temp_vm_name):
        print("RHEVM:{} temp VM could not be provisioned".format(provider))
        sys.exit(127)
    print("RHEVM:{} successfully provisioned temp vm".format(provider))


def check_disks(api, temp_vm_name):
    disks = api.vms.get(temp_vm_name).disks.list()
    for disk in disks:
        if disk.get_status().state != "ok":
            return False
    return True


# sometimes, rhevm is just not cooperative. This is function used to wait for template on
# export domain to become unlocked
def check_edomain_template(api, edomain, temp_template_name):
    '''
    checks for the edomain templates status, and returns True, if template state is ok
    otherwise returns False. try, except block returns the False in case of Exception,
    as wait_for handles the timeout Exceptions.
    :param api: API to chosen RHEVM provider.
    :param edomain: export domain.
    :return: True or False based on the template status.
    '''
    try:
        template = api.storagedomains.get(edomain).templates.get(temp_template_name)
        if template.get_status().state != "ok":
            return False
        return True
    except Exception:
        return False


# verify the template deletion
def is_edomain_template_deleted(api, name, edomain):
    return not api.storagedomains.get(edomain).templates.get(name)


def add_disk_to_vm(api, sdomain, disk_size, disk_format, disk_interface, temp_vm_name,
                   provider):
    """Adds second disk to a temporary VM.

    Args:
        api: API to chosen RHEVM provider.
        sdomain: Storage domain to save new disk onto.
        disk_size: Size of the new disk (in B).
        disk_format: Format of the new disk.
        disk_interface: Interface of the new disk.
    """
    if len(api.vms.get(temp_vm_name).disks.list()) > 1:
        print("RHEVM:{} Warning: found more than one disk in existing VM.".format(provider))
        print("RHEVM:{} Skipping this step, attempting to continue...".format(provider))
        return
    actual_sdomain = api.storagedomains.get(sdomain)
    temp_vm = api.vms.get(temp_vm_name)
    params_disk = params.Disk(storage_domain=actual_sdomain, size=disk_size,
                              interface=disk_interface, format=disk_format)
    temp_vm.disks.add(params_disk)

    wait_for(check_disks, [api, temp_vm_name], fail_condition=False, delay=5, num_sec=900)

    # check, if there are two disks
    if len(api.vms.get(temp_vm_name).disks.list()) < 2:
        print("RHEVM:{} Disk failed to add".format(provider))
        sys.exit(127)
    print("RHEVM:{} Successfully added Disk".format(provider))


def templatize_vm(api, template_name, cluster, temp_vm_name, provider):
    """Templatizes temporary VM. Result is template with two disks.

    Args:
        api: API to chosen RHEVM provider.
        template_name: Name of the final template.
        cluster: Cluster to save the final template onto.
    """
    if api.templates.get(template_name) is not None:
        print("RHEVM:{} Warning: found finished template with this name.".format(provider))
        print("RHEVM:{} Skipping this step, attempting to continue...".format(provider))
        return
    temporary_vm = api.vms.get(temp_vm_name)
    actual_cluster = api.clusters.get(cluster)
    new_template = params.Template(name=template_name, vm=temporary_vm, cluster=actual_cluster)
    api.templates.add(new_template)

    wait_for(check_disks, [api, temp_vm_name], fail_condition=False, delay=5, num_sec=900)

    # check, if template is really there
    if not api.templates.get(template_name):
        print("RHEVM:{} templatizing temporary VM failed".format(provider))
        sys.exit(127)
    print("RHEVM:{} successfully templatized the temporary VM".format(provider))


# get the domain edomain path on the rhevm
def get_edomain_path(api, edomain):
    edomain_id = api.storagedomains.get(edomain).get_id()
    edomain_conn = api.storagedomains.get(edomain).storageconnections.list()[0]
    return (edomain_conn.get_path() + '/' + edomain_id,
            edomain_conn.get_address())


def cleanup_empty_dir_on_edomain(path, edomainip, sshname, sshpass, provider_ip, provider):
    """Cleanup all the empty directories on the edomain/edomain_id/master/vms
    else api calls will result in 400 Error with ovf not found,
    Args:
        path: path for vms directory on edomain.
        edomain: Export domain of chosen RHEVM provider.
        edomainip: edomainip to connect through ssh.
        sshname: edomain ssh credentials.
        sshpass: edomain ssh credentials.
        provider: provider under execution
        provider_ip: provider ip address
    """
    try:
        ssh_client = make_ssh_client(provider_ip, sshname, sshpass)
        edomain_path = edomainip + ':' + path
        command = 'mkdir -p ~/tmp_filemount && mount -O tcp {} ~/tmp_filemount &&'.format(
            edomain_path)
        command += 'cd ~/tmp_filemount/master/vms &&'
        command += 'find . -maxdepth 1 -type d -empty -delete &&'
        command += 'cd ~ && umount ~/tmp_filemount &&'
        command += 'find . -maxdepth 1 -name tmp_filemount -type d -empty -delete'
        print("RHEVM:{} Deleting the empty directories on edomain/vms file...".format(provider))
        exit_status, output = ssh_client.run_command(command)
        ssh_client.close()
        if exit_status != 0:
            print("RHEVM:{} Error while deleting the empty directories on path..".format(
                provider))
            print(output)
        print("RHEVM:{} successfully deleted the empty directories on path..".format(provider))
    except Exception as e:
        print(e)
        return False


def cleanup(api, edomain, ssh_client, ovaname, provider, temp_template_name, temp_vm_name):
    """Cleans up all the mess that the previous functions left behind.

    Args:
        api: API to chosen RHEVM provider.
        edomain: Export domain of chosen RHEVM provider.
    """
    try:
        print("RHEVM:{} Deleting the  .ova file...".format(provider))
        command = 'rm {}'.format(ovaname)
        exit_status, output = ssh_client.run_command(command)

        print("RHEVM:{} Deleting the temp_vm on sdomain...".format(provider))
        temporary_vm = api.vms.get(temp_vm_name)
        if temporary_vm:
            temporary_vm.delete()

        print("RHEVM:{} Deleting the temp_template on sdomain...".format(provider))
        temporary_template = api.templates.get(temp_template_name)
        if temporary_template:
            temporary_template.delete()

        # waiting for template on export domain
        unimported_template = api.storagedomains.get(edomain).templates.get(
            temp_template_name)
        print("RHEVM:{} waiting for template on export domain...".format(provider))
        wait_for(check_edomain_template, [api, edomain, temp_template_name],
                 fail_condition=False, delay=5)

        if unimported_template:
            print("RHEVM:{} deleting the template on export domain...".format(provider))
            unimported_template.delete()

        print("RHEVM:{} waiting for template delete on export domain...".format(provider))
        wait_for(is_edomain_template_deleted, [api, temp_template_name, edomain],
                 fail_condition=False, delay=5)
        print("RHEVM:{} successfully deleted template on export domain...".format(provider))

    except Exception as e:
        print(e)
        print("RHEVM:{} Exception occurred in cleanup method".format(provider))
        return False


def api_params_resolution(item_list, item_name, item_param):
    """Picks and prints info about parameter obtained by api call.

    Args:
        item_list: List of possible candidates to pick from.
        item_name: Name of parameter obtained by api call.
        item_param: Name of parameter representing data in the script.
    """
    if len(item_list) == 0:
        print("RHEVM: Cannot find {} ({}) automatically.".format(item_name, item_param))
        print("Please specify it by cmd-line parameter '--{}' or in cfme_data.".format(item_param))
        return None
    elif len(item_list) > 1:
        print("RHEVM: Found multiple instances of {}. Picking '{}'.".format(
            item_name, item_list[0]))
    else:
        print("RHEVM: Found {} '{}'.".format(item_name, item_list[0]))

    return item_list[0]


def get_edomain(api):
    """Discovers suitable export domain automatically.

    Args:
        api: API to RHEVM instance.
    """
    edomain_names = []

    for domain in api.storagedomains.list(status=None):
        if domain.get_type() == 'export':
            edomain_names.append(domain.get_name())

    return api_params_resolution(edomain_names, 'export domain', 'edomain')


def get_sdomain(api):
    """Discovers suitable storage domain automatically.

    Args:
        api: API to RHEVM instance.
    """
    sdomain_names = []

    for domain in api.storagedomains.list(status=None):
        if domain.get_type() == 'data':
            sdomain_names.append(domain.get_name())

    return api_params_resolution(sdomain_names, 'storage domain', 'sdomain')


def get_cluster(api):
    """Discovers suitable cluster automatically.

    Args:
        api: API to RHEVM instance.
    """
    cluster_names = []

    for cluster in api.clusters.list():
        for host in api.hosts.list():
            if host.get_cluster().id == cluster.id:
                cluster_names.append(cluster.get_name())

    return api_params_resolution(cluster_names, 'cluster', 'cluster')


def check_kwargs(**kwargs):
    for key, val in kwargs.iteritems():
        if val is None:
            print("RHEVM: please supply required parameter '{}'.".format(key))
            sys.exit(127)


def update_params_api(api, **kwargs):
    """Updates parameters with ones determined from api call.

    Args:
        api: API to RHEVM instance.
        kwargs: Kwargs generated from cfme_data['template_upload']['template_upload_rhevm']
    """
    if kwargs.get('edomain') is None:
        kwargs['edomain'] = get_edomain(api)
    if kwargs.get('sdomain') is None:
        kwargs['sdomain'] = get_sdomain(api)
    if kwargs.get('cluster') is None:
        kwargs['cluster'] = get_cluster(api)

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


def make_kwargs_rhevm(cfmeqe_data, provider):
    data = cfmeqe_data['management_systems'][provider]
    temp_up = cfme_data['template_upload']['template_upload_rhevm']

    edomain = data['template_upload'].get('edomain', None)
    sdomain = data['template_upload'].get('sdomain', None)
    cluster = data['template_upload'].get('cluster', None)
    disk_size = temp_up.get('disk_size', None)
    disk_format = temp_up.get('disk_format', None)
    disk_interface = temp_up.get('disk_interface', None)

    kwargs = {'provider': provider}
    if edomain:
        kwargs['edomain'] = edomain
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

    return kwargs


def upload_template(rhevip, sshname, sshpass, username, password,
                    provider, image_url, template_name, provider_data, stream):
    try:
        print("RHEVM:{} Template {} upload started".format(provider, template_name))
        if provider_data:
            kwargs = make_kwargs_rhevm(provider_data, provider)
            providers = provider_data['management_systems']
            api = get_mgmt(kwargs.get('provider'), providers=providers).api
        else:
            kwargs = make_kwargs_rhevm(cfme_data, provider)
            api = get_mgmt(kwargs.get('provider')).api
        kwargs['image_url'] = image_url
        kwargs['template_name'] = template_name
        ovaname = get_ova_name(image_url)
        ssh_client = make_ssh_client(rhevip, sshname, sshpass)
        temp_template_name = ('auto-tmp-{}-'.format(
            fauxfactory.gen_alphanumeric(8))) + template_name
        temp_vm_name = ('auto-vm-{}-'.format(
            fauxfactory.gen_alphanumeric(8))) + template_name
        if template_name is None:
            template_name = cfme_data['basic_info']['appliance_template']

        path, edomain_ip = get_edomain_path(api, kwargs.get('edomain'))

        kwargs = update_params_api(api, **kwargs)

        check_kwargs(**kwargs)

        if api.templates.get(template_name) is not None:
            print("RHEVM:{} Found finished template with name {}.".format(provider, template_name))
            print("RHEVM:{} The script will now end.".format(provider))
            ssh_client.close()
        else:
            print("RHEVM:{} Downloading .ova file...".format(provider))
            download_ova(ssh_client, kwargs.get('image_url'))
            try:
                print("RHEVM:{} Templatizing .ova file...".format(provider))
                template_from_ova(api, username, password, rhevip, kwargs.get('edomain'),
                                  ovaname, ssh_client, temp_template_name, provider)
                print("RHEVM:{} Importing new template to data domain...".format(provider))
                import_template(api, kwargs.get('edomain'), kwargs.get('sdomain'),
                                kwargs.get('cluster'), temp_template_name, provider)
                print("RHEVM:{} Making a temporary VM from new template...".format(provider))
                make_vm_from_template(api, kwargs.get('cluster'), temp_template_name, temp_vm_name,
                                      provider)
                print("RHEVM:{} Adding disk to created VM...".format(provider))
                add_disk_to_vm(api, kwargs.get('sdomain'), kwargs.get('disk_size'),
                               kwargs.get('disk_format'), kwargs.get('disk_interface'),
                               temp_vm_name, provider)
                print("RHEVM:{} Templatizing VM...".format(provider))
                templatize_vm(api, template_name, kwargs.get('cluster'), temp_vm_name, provider)
                print("RHEVM:{} Adding template {} to trackerbot..".format(provider, template_name))
                trackerbot.trackerbot_add_provider_template(stream, provider, template_name)
            finally:
                cleanup(api, kwargs.get('edomain'), ssh_client, ovaname, provider,
                        temp_template_name, temp_vm_name)
                change_edomain_state(api, 'maintenance', kwargs.get('edomain'), provider)
                cleanup_empty_dir_on_edomain(path, edomain_ip,
                                             sshname, sshpass, rhevip, provider)
                change_edomain_state(api, 'active', kwargs.get('edomain'), provider)
                ssh_client.close()
                api.disconnect()
                print("RHEVM:{} Template {} upload Ended".format(provider, template_name))
        if provider_data and api.templates.get(template_name):
            print("RHEVM:{} Deploying Template {}....".format(provider, template_name))
            vm_name = 'test_{}_{}'.format(template_name, fauxfactory.gen_alphanumeric(8))
            deploy_args = {'provider': provider, 'vm_name': vm_name,
                           'template': template_name, 'deploy': True}
            getattr(__import__('clone_template'), "main")(**deploy_args)
        print("RHEVM:{} Template {} upload Ended".format(provider, template_name))
    except Exception as e:
        print(e)
        return False


def run(**kwargs):
    """Calls all the functions needed to upload new template to RHEVM.
       This is called either by template_upload_all script, or by main function.

    Args:
        **kwargs: Kwargs generated from cfme_data['template_upload']['template_upload_rhevm'].
    """
    thread_queue = []
    valid_providers = []

    providers = list_providers("rhevm")
    if kwargs['provider_data']:
        mgmt_sys = providers = kwargs['provider_data']['management_systems']
    for provider in providers:
        if kwargs['provider_data']:
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
        print("RHEVM:{} verifying provider's state before template upload".format(provider))
        if not net.is_pingable(rhevip):
            continue
        elif not is_ovirt_engine_running(rhevip, sshname, sshpass):
            print('RHEVM:{} ovirt-engine service not running..'.format(provider))
            continue
        valid_providers.append(provider)

    for provider in valid_providers:
        if kwargs['provider_data']:
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
                              kwargs['provider_data'], kwargs['stream']))
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
