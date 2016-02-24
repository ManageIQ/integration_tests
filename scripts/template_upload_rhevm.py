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

from ovirtsdk.api import API
from ovirtsdk.xml import params

from utils.conf import cfme_data
from utils.conf import credentials
from utils.ssh import SSHClient
from utils.wait import wait_for


# temporary vm name (this vm will be deleted)
TEMP_VM_NAME = 'auto-vm-%s' % fauxfactory.gen_alphanumeric(8)
# temporary template name (this template will be deleted)
TEMP_TMP_NAME = 'auto-tmp-%s' % fauxfactory.gen_alphanumeric(8)


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


def change_edomain_state(api, state, edomain):
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
                print '{} successfully set to {} state'.format(edomain, state)
                return True
        return False
    except Exception:
        print "Exception occurred while changing {} state to {}".format(edomain, state)
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
    command = 'curl -O %s' % ovaurl
    exit_status, output = ssh_client.run_command(command)
    if exit_status != 0:
        print "RHEVM: There was an error while downloading ova file:"
        print output
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
        print "RHEVM: Warning: found another template with this name."
        print "RHEVM: Skipping this step. Attempting to continue..."
        return
    command = ['rhevm-image-uploader']
    command.append("-u %s" % username)
    command.append("-p %s" % password)
    command.append("-r %s:443" % rhevip)
    command.append("-N %s" % TEMP_TMP_NAME)
    command.append("-e %s" % edomain)
    command.append("upload %s" % ovaname)
    command.append("-m --insecure")
    exit_status, output = ssh_client.run_command(' '.join(command))
    if exit_status != 0:
        print "RHEVM: There was an error while making template from ova file:"
        print output
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
        print "RHEVM: Warning: found another template with this name."
        print "RHEVM: Skipping this step, attempting to continue..."
        return
    actual_template = api.storagedomains.get(edomain).templates.get(TEMP_TMP_NAME)
    actual_storage_domain = api.storagedomains.get(sdomain)
    actual_cluster = api.clusters.get(cluster)
    import_action = params.Action(async=False, cluster=actual_cluster,
                                  storage_domain=actual_storage_domain)
    actual_template.import_template(action=import_action)
    # Check if the template is really there
    if not api.templates.get(TEMP_TMP_NAME):
        print "RHEVM: The template failed to import"
        sys.exit(127)


def make_vm_from_template(api, cluster):
    """Makes temporary VM from imported template. This template will be later deleted.
       It's used to add a new disk and to convert back to template.

    Args:
        api: API to chosen RHEVM provider.
        cluster: Cluster to save the temporary VM on.
    """
    if api.vms.get(TEMP_VM_NAME) is not None:
        print "RHEVM: Warning: found another VM with this name."
        print "RHEVM: Skipping this step, attempting to continue..."
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
        print "RHEVM: VM could not be provisioned"
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
    template = api.storagedomains.get(edomain).templates.get(TEMP_TMP_NAME)
    if template.get_status().state != "ok":
        return False
    return True


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
        print "RHEVM: Warning: found more than one disk in existing VM."
        print "RHEVM: Skipping this step, attempting to continue..."
        return
    actual_sdomain = api.storagedomains.get(sdomain)
    temp_vm = api.vms.get(TEMP_VM_NAME)
    params_disk = params.Disk(storage_domain=actual_sdomain, size=disk_size,
                              interface=disk_interface, format=disk_format)
    temp_vm.disks.add(params_disk)

    wait_for(check_disks, [api], fail_condition=False, delay=5, num_sec=900)

    # check, if there are two disks
    if len(api.vms.get(TEMP_VM_NAME).disks.list()) < 2:
        print "RHEVM: Disk failed to add"
        sys.exit(127)


def templatize_vm(api, template_name, cluster):
    """Templatizes temporary VM. Result is template with two disks.

    Args:
        api: API to chosen RHEVM provider.
        template_name: Name of the final template.
        cluster: Cluster to save the final template onto.
    """
    if api.templates.get(template_name) is not None:
        print "RHEVM: Warning: found finished template with this name."
        print "RHEVM: Skipping this step, attempting to continue..."
        return
    temporary_vm = api.vms.get(TEMP_VM_NAME)
    actual_cluster = api.clusters.get(cluster)
    new_template = params.Template(name=template_name, vm=temporary_vm, cluster=actual_cluster)
    api.templates.add(new_template)

    wait_for(check_disks, [api], fail_condition=False, delay=5, num_sec=900)

    # check, if template is really there
    if not api.templates.get(template_name):
        print "RHEVM: VM failed to templatize"
        sys.exit(127)


# get the domain edomain path on the rhevm
def get_edomain_path(api, edomain):
    edomain_id = api.storagedomains.get(edomain).get_id()
    edomain_conn = api.storagedomains.get(edomain).storageconnections.list()[0]
    return (edomain_conn.get_path() + '/' + edomain_id,
            edomain_conn.get_address())


def cleanup_empty_dir_on_edomain(path, edomainip, sshname, sshpass):
    """Cleanup all the empty directories on the edomain/edomain_id/master/vms
    else api calls will result in 400 Error with ovf not found,

    Args:
        api: API to chosen RHEVM provider.
        edomain: Export domain of chosen RHEVM provider.
        edomainip: edomainip to connect through ssh.
        sshname: edomain ssh credentials.
        sshpass: edomain ssh credentials.
    """
    print "RHEVM: Deleting the empty directories on edomain/vms file..."
    ssh_client = make_ssh_client(edomainip, sshname, sshpass)
    command = 'cd {}/master/vms && find . -maxdepth 1 -type d -empty -delete'.format(path)
    exit_status, output = ssh_client.run_command(command)
    if exit_status != 0:
        print "RHEVM: Error while deleting the empty directories on path.."
        print output


def cleanup(api, edomain, ssh_client, ovaname):
    """Cleans up all the mess that the previous functions left behind.

    Args:
        api: API to chosen RHEVM provider.
        edomain: Export domain of chosen RHEVM provider.
    """
    try:
        print "RHEVM: Deleting the  .ova file..."
        command = 'rm %s' % ovaname
        exit_status, output = ssh_client.run_command(command)

        print "RHEVM: Deleting the temp_vm on sdomain..."
        temporary_vm = api.vms.get(TEMP_VM_NAME)
        if temporary_vm:
            temporary_vm.delete()

        print "RHEVM: Deleting the temp_template on sdomain..."
        temporary_template = api.templates.get(TEMP_TMP_NAME)
        if temporary_template:
            temporary_template.delete()

        # waiting for template on export domain
        unimported_template = api.storagedomains.get(edomain).templates.get(
            TEMP_TMP_NAME)
        print "RHEVM: waiting for template on export domain..."
        wait_for(check_edomain_template, [unimported_template],
                 fail_condition=False, delay=5)

        if unimported_template:
            print "RHEVM: deleting the template on export domain..."
            unimported_template.delete()

        print "RHEVM: waiting for template delete on export domain..."
        wait_for(is_edomain_template_deleted, [unimported_template],
                 fail_condition=False, delay=5)

    except Exception:
        print "RHEVM: Exception occurred in cleanup method"
        return False


def api_params_resolution(item_list, item_name, item_param):
    """Picks and prints info about parameter obtained by api call.

    Args:
        item_list: List of possible candidates to pick from.
        item_name: Name of parameter obtained by api call.
        item_param: Name of parameter representing data in the script.
    """
    if len(item_list) == 0:
        print "RHEVM: Cannot find %s (%s) automatically." % (item_name, item_param)
        print "Please specify it by cmd-line parameter '--%s' or in cfme_data." % item_param
        return None
    elif len(item_list) > 1:
        print "RHEVM: Found multiple instances of %s. Picking '%s'." % (item_name, item_list[0])
    else:
        print "RHEVM: Found %s '%s'." % (item_name, item_list[0])

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
            print "RHEVM: please supply required parameter '%s'." % key
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


def run(**kwargs):
    """Calls all the functions needed to upload new template to RHEVM.
       This is called either by template_upload_all script, or by main function.

    Args:
        **kwargs: Kwargs generated from cfme_data['template_upload']['template_upload_rhevm'].
    """
    ovaname = get_ova_name(kwargs.get('image_url'))

    mgmt_sys = cfme_data['management_systems'][kwargs.get('provider')]

    rhevurl = mgmt_sys['hostname']
    rhevm_credentials = mgmt_sys['credentials']
    username = credentials[rhevm_credentials]['username']
    password = credentials[rhevm_credentials]['password']
    ssh_rhevm_creds = mgmt_sys['hosts'][0]['credentials']
    sshname = credentials[ssh_rhevm_creds]['username']
    sshpass = credentials[ssh_rhevm_creds]['password']
    rhevip = mgmt_sys['ipaddress']

    apiurl = 'https://%s:443/api' % rhevurl

    ssh_client = make_ssh_client(rhevip, sshname, sshpass)
    api = API(url=apiurl, username=username, password=password,
              insecure=True, persistent_auth=False)

    template_name = kwargs.get('template_name', None)
    if template_name is None:
        template_name = cfme_data['basic_info']['appliance_template']

    path, edomain_ip = get_edomain_path(api, kwargs.get('edomain'))

    kwargs = update_params_api(api, **kwargs)

    check_kwargs(**kwargs)

    if api.templates.get(template_name) is not None:
        print "RHEVM: Found finished template with this name."
        print "RHEVM: The script will now end."
    else:
        print "RHEVM: Downloading .ova file..."
        download_ova(ssh_client, kwargs.get('image_url'))
        try:
            print "RHEVM: Templatizing .ova file..."
            template_from_ova(api, username, password, rhevip, kwargs.get('edomain'),
                              ovaname, ssh_client)
            print "RHEVM: Importing new template..."
            import_template(api, kwargs.get('edomain'), kwargs.get('sdomain'),
                            kwargs.get('cluster'))
            print "RHEVM: Making a temporary VM from new template..."
            make_vm_from_template(api, kwargs.get('cluster'))
            print "RHEVM: Adding disk to created VM..."
            add_disk_to_vm(api, kwargs.get('sdomain'), kwargs.get('disk_size'),
                           kwargs.get('disk_format'), kwargs.get('disk_interface'))
            print "RHEVM: Templatizing VM..."
            templatize_vm(api, template_name, kwargs.get('cluster'))
        finally:
            change_edomain_state(api, 'maintenance', kwargs.get('edomain'))
            cleanup(api, kwargs.get('edomain'), ssh_client, ovaname)
            cleanup_empty_dir_on_edomain(path, edomain_ip,
                                         sshname, sshpass)
            change_edomain_state(api, 'active', kwargs.get('edomain'))
            ssh_client.close()
            api.disconnect()

    print "RHEVM: Done."


if __name__ == "__main__":
    args = parse_cmd_line()

    kwargs = cfme_data['template_upload']['template_upload_rhevm']

    final_kwargs = make_kwargs(args, cfme_data, **kwargs)

    run(**final_kwargs)
