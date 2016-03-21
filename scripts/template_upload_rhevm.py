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
import sys
from threading import Lock, Thread

from ovirtsdk.xml import params

from utils import net
from utils.conf import cfme_data
from utils.conf import credentials
from utils.providers import get_mgmt, list_providers
from utils.ssh import SSHClient
from utils.wait import wait_for

lock = Lock()

# temporary vm name (this vm will be deleted)
TEMP_VM_NAME = 'auto-vm-{}'.format(fauxfactory.gen_alphanumeric(8))
# temporary template name (this template will be deleted)
TEMP_TMP_NAME = 'auto-tmp-{}'.format(fauxfactory.gen_alphanumeric(8))


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

                wait_for(is_edomain_template_deleted,
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


def template_from_ova(api, username, password, rhevip, edomain, ovaname, ssh_client):
    """Uses rhevm-image-uploader to make a template from ova file.

    Args:
        api: API for RHEVM.
        username: Username to chosen RHEVM provider.
        password: Password to chosen RHEVM provider.
        rhevip: IP of chosen RHEVM provider.
        edomain: Export domain of selected RHEVM provider.
        ovaname: Name of ova file.
        ssh_client: :py:class:`utils.ssh.SSHClient` instance
    """
    if api.storagedomains.get(edomain).templates.get(TEMP_TMP_NAME) is not None:
        print("RHEVM: Warning: found another template with this name.")
        print("RHEVM: Skipping this step. Attempting to continue...")
        return
    command = ['rhevm-image-uploader']
    command.append("-u {}".format(username))
    command.append("-p {}".format(password))
    command.append("-r {}:443".format(rhevip))
    command.append("-N {}".format(TEMP_TMP_NAME))
    command.append("-e {}".format(edomain))
    command.append("upload {}".format(ovaname))
    command.append("-m --insecure")
    exit_status, output = ssh_client.run_command(' '.join(command))
    if exit_status != 0:
        print("RHEVM: There was an error while making template from ova file:")
        print(output)
        sys.exit(127)


def import_template(api, edomain, sdomain, cluster):
    """Imports template from export domain to storage domain.

    Args:
        api: API to RHEVM instance.
        edomain: Export domain of selected RHEVM provider.
        sdomain: Storage domain of selected RHEVM provider.
        cluster: Cluster to save imported template on.
    """
    if api.templates.get(TEMP_TMP_NAME) is not None:
        print("RHEVM: Warning: found another template with this name.")
        print("RHEVM: Skipping this step, attempting to continue...")
        return
    actual_template = api.storagedomains.get(edomain).templates.get(TEMP_TMP_NAME)
    actual_storage_domain = api.storagedomains.get(sdomain)
    actual_cluster = api.clusters.get(cluster)
    import_action = params.Action(async=False, cluster=actual_cluster,
                                  storage_domain=actual_storage_domain)
    actual_template.import_template(action=import_action)
    # Check if the template is really there
    if not api.templates.get(TEMP_TMP_NAME):
        print("RHEVM: The template failed to import")
        sys.exit(127)


def make_vm_from_template(api, cluster):
    """Makes temporary VM from imported template. This template will be later deleted.
       It's used to add a new disk and to convert back to template.

    Args:
        api: API to chosen RHEVM provider.
        cluster: Cluster to save the temporary VM on.
    """
    if api.vms.get(TEMP_VM_NAME) is not None:
        print("RHEVM: Warning: found another VM with this name.")
        print("RHEVM: Skipping this step, attempting to continue...")
        return
    actual_template = api.templates.get(TEMP_TMP_NAME)
    actual_cluster = api.clusters.get(cluster)
    params_vm = params.VM(name=TEMP_VM_NAME, template=actual_template, cluster=actual_cluster)
    api.vms.add(params_vm)

    # we must wait for the vm do become available
    def check_status():
        status = api.vms.get(TEMP_VM_NAME).get_status()
        if status.state != 'down':
            return False
        return True

    wait_for(check_status, fail_condition=False, delay=5)

    # check, if the vm is really there
    if not api.vms.get(TEMP_VM_NAME):
        print("RHEVM: VM could not be provisioned")
        sys.exit(127)


def check_disks(api):
    disks = api.vms.get(TEMP_VM_NAME).disks.list()
    for disk in disks:
        if disk.get_status().state != "ok":
            return False
    return True


# sometimes, rhevm is just not cooperative. This is function used to wait for template on
# export domain to become unlocked
def check_edomain_template(api, edomain):
    '''
    checks for the edomain templates status, and returns True, if template state is ok
    otherwise returns False. try, except block returns the False in case of Exception,
    as wait_for handles the timeout Exceptions.
    :param api: API to chosen RHEVM provider.
    :param edomain: export domain.
    :return: True or False based on the template status.
    '''
    try:
        template = api.storagedomains.get(edomain).templates.get(TEMP_TMP_NAME)
        if template.get_status().state != "ok":
            return False
        return True
    except Exception:
        return False


# verify the template deletion
def is_edomain_template_deleted(api, name, edomain):
    return not api.storagedomains.get(edomain).templates.get(name)


def add_disk_to_vm(api, sdomain, disk_size, disk_format, disk_interface):
    """Adds second disk to a temporary VM.

    Args:
        api: API to chosen RHEVM provider.
        sdomain: Storage domain to save new disk onto.
        disk_size: Size of the new disk (in B).
        disk_format: Format of the new disk.
        disk_interface: Interface of the new disk.
    """
    if len(api.vms.get(TEMP_VM_NAME).disks.list()) > 1:
        print("RHEVM: Warning: found more than one disk in existing VM.")
        print("RHEVM: Skipping this step, attempting to continue...")
        return
    actual_sdomain = api.storagedomains.get(sdomain)
    temp_vm = api.vms.get(TEMP_VM_NAME)
    params_disk = params.Disk(storage_domain=actual_sdomain, size=disk_size,
                              interface=disk_interface, format=disk_format)
    temp_vm.disks.add(params_disk)

    wait_for(check_disks, [api], fail_condition=False, delay=5, num_sec=900)

    # check, if there are two disks
    if len(api.vms.get(TEMP_VM_NAME).disks.list()) < 2:
        print("RHEVM: Disk failed to add")
        sys.exit(127)


def templatize_vm(api, template_name, cluster):
    """Templatizes temporary VM. Result is template with two disks.

    Args:
        api: API to chosen RHEVM provider.
        template_name: Name of the final template.
        cluster: Cluster to save the final template onto.
    """
    if api.templates.get(template_name) is not None:
        print("RHEVM: Warning: found finished template with this name.")
        print("RHEVM: Skipping this step, attempting to continue...")
        return
    temporary_vm = api.vms.get(TEMP_VM_NAME)
    actual_cluster = api.clusters.get(cluster)
    new_template = params.Template(name=template_name, vm=temporary_vm, cluster=actual_cluster)
    api.templates.add(new_template)

    wait_for(check_disks, [api], fail_condition=False, delay=5, num_sec=900)

    # check, if template is really there
    if not api.templates.get(template_name):
        print("RHEVM: VM failed to templatize")
        sys.exit(127)


# get the domain edomain path on the rhevm
def get_edomain_path(api, edomain):
    edomain_id = api.storagedomains.get(edomain).get_id()
    edomain_conn = api.storagedomains.get(edomain).storageconnections.list()[0]
    return (edomain_conn.get_path() + '/' + edomain_id,
            edomain_conn.get_address())


def cleanup_empty_dir_on_edomain(path, edomainip, sshname, sshpass, provider):
    """Cleanup all the empty directories on the edomain/edomain_id/master/vms
    else api calls will result in 400 Error with ovf not found,

    Args:
        api: API to chosen RHEVM provider.
        edomain: Export domain of chosen RHEVM provider.
        edomainip: edomainip to connect through ssh.
        sshname: edomain ssh credentials.
        sshpass: edomain ssh credentials.
    """
    try:
        print("RHEVM:{} Deleting the empty directories on edomain/vms file...".format(provider))
        ssh_client = make_ssh_client(edomainip, sshname, sshpass)
        command = 'cd {}/master/vms && find . -maxdepth 1 -type d -empty -delete'.format(path)
        exit_status, output = ssh_client.run_command(command)
        if exit_status != 0:
            print("RHEVM:{} Error while deleting the empty directories on path..".format(provider))
            print(output)
    except Exception:
        return False


def cleanup(api, edomain, ssh_client, ovaname, provider):
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
        temporary_vm = api.vms.get(TEMP_VM_NAME)
        if temporary_vm:
            temporary_vm.delete()

        print("RHEVM: Deleting the temp_template on sdomain...".format(provider))
        temporary_template = api.templates.get(TEMP_TMP_NAME)
        if temporary_template:
            temporary_template.delete()

        # waiting for template on export domain
        unimported_template = api.storagedomains.get(edomain).templates.get(
            TEMP_TMP_NAME)
        print("RHEVM:{} waiting for template on export domain...".format(provider))
        wait_for(check_edomain_template, [unimported_template],
                 fail_condition=False, delay=5)

        if unimported_template:
            print("RHEVM: deleting the template on export domain...".format(provider))
            unimported_template.delete()

        print("RHEVM: waiting for template delete on export domain...".format(provider))
        wait_for(is_edomain_template_deleted, [unimported_template],
                 fail_condition=False, delay=5)

    except Exception:
        print("RHEVM: Exception occurred in cleanup method".format(provider))
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


def make_kwargs_rhevm(cfme_data, provider):
    data = cfme_data['management_systems'][provider]
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
                    provider, image_url, template_name):
    try:
        print("RHEVM:{} Template {} upload started".format(provider, template_name))
        kwargs = make_kwargs_rhevm(cfme_data, provider)
        kwargs['image_url'] = image_url
        kwargs['template_name'] = template_name
        ovaname = get_ova_name(image_url)
        ssh_client = make_ssh_client(rhevip, sshname, sshpass)
        api = get_mgmt(kwargs.get('provider')).api

        if template_name is None:
            template_name = cfme_data['basic_info']['appliance_template']

        path, edomain_ip = get_edomain_path(api, kwargs.get('edomain'))

        kwargs = update_params_api(api, **kwargs)

        check_kwargs(**kwargs)

        if api.templates.get(template_name) is not None:
            print("RHEVM:{} Found finished template with name {}.".format(provider, template_name))
            print("RHEVM:{} The script will now end.".format(provider))
        else:
            print("RHEVM:{} Downloading .ova file...".format(provider))
            download_ova(ssh_client, kwargs.get('image_url'))
            try:
                print("RHEVM:{} Templatizing .ova file...".format(provider))
                template_from_ova(api, username, password, rhevip, kwargs.get('edomain'),
                                  ovaname, ssh_client)
                print("RHEVM:{} Importing new template...".format(provider))
                import_template(api, kwargs.get('edomain'), kwargs.get('sdomain'),
                                kwargs.get('cluster'))
                print("RHEVM:{} Making a temporary VM from new template...".format(provider))
                make_vm_from_template(api, kwargs.get('cluster'))
                print("RHEVM:{} Adding disk to created VM...".format(provider))
                add_disk_to_vm(api, kwargs.get('sdomain'), kwargs.get('disk_size'),
                               kwargs.get('disk_format'), kwargs.get('disk_interface'))
                print("RHEVM:{} Templatizing VM...".format(provider))
                templatize_vm(api, template_name, kwargs.get('cluster'))
            finally:
                cleanup(api, kwargs.get('edomain'), ssh_client, ovaname, provider)
                change_edomain_state(api, 'maintenance', kwargs.get('edomain'), provider)
                cleanup_empty_dir_on_edomain(path, edomain_ip,
                                sshname, sshpass, provider)
                change_edomain_state(api, 'active', kwargs.get('edomain'), provider)
                ssh_client.close()
                api.disconnect()
                print("RHEVM:{} Template {} upload Ended".format(provider, template_name))
        print("RHEVM: Done.")
    except Exception as e:
        print(e)
        return False


def run(**kwargs):
    """Calls all the functions needed to upload new template to RHEVM.
       This is called either by template_upload_all script, or by main function.

    Args:
        **kwargs: Kwargs generated from cfme_data['template_upload']['template_upload_rhevm'].
    """
    mgmt_sys = cfme_data['management_systems']
    thread_queue = []
    valid_providers = []
    for provider in list_providers("rhevm"):
        ssh_rhevm_creds = mgmt_sys[provider]['hosts'][0]['credentials']
        sshname = credentials[ssh_rhevm_creds]['username']
        sshpass = credentials[ssh_rhevm_creds]['password']
        print("RHEVM:{} verifying provider's state before template upload".format(provider))
        if not net.is_pingable(cfme_data['management_systems'][provider]['ipaddress']):
            continue
        elif not is_ovirt_engine_running(cfme_data['management_systems'][provider]['ipaddress'],
                                         sshname, sshpass):
            print('RHEVM:{} ovirt-engine service not running..'.format(provider))
            continue
        valid_providers.append(provider)

    for provider in valid_providers:
        ssh_rhevm_creds = mgmt_sys[provider]['hosts'][0]['credentials']
        sshname = credentials[ssh_rhevm_creds]['username']
        sshpass = credentials[ssh_rhevm_creds]['password']
        rhevm_credentials = mgmt_sys[provider]['credentials']
        username = credentials[rhevm_credentials]['username']
        password = credentials[rhevm_credentials]['password']
        rhevip = mgmt_sys[provider]['ipaddress']
        thread = Thread(target=upload_template,
                        args=(rhevip, sshname, sshpass, username, password, provider,
                              kwargs.get('image_url'), kwargs.get('template_name')))
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
