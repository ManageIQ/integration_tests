#!/usr/bin/python

"""Please check your cfme_data and credentials. This script needs some valid
data from those files

Please, place all the function calls into the function 'run(**kwargs)'.
"""

import argparse
import sys

from ovirtsdk.api import API
from ovirtsdk.xml import params

from utils.conf import cfme_data
from utils.conf import credentials
from utils.ssh import SSHClient
from utils.wait import wait_for


#temporary vm name (this vm will be deleted)
TEMP_VM_NAME = 'automated-temporary'
#temporary template name (this template will be deleted)
TEMP_TMP_NAME = 'automated-template-temporary'


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument("--image_url", dest="image_url",
                        help="URL of ova file to upload", required=True)
    parser.add_argument("--template_name", dest="template_name",
                        help="Name of the new template", required=True)
    parser.add_argument("--edomain", dest="edomain",
                        help="Export domain for the remplate", required=True)
    parser.add_argument("--sdomain", dest="sdomain",
                        help="Storage domain for vm and disk", required=True)
    parser.add_argument("--cluster", dest="cluster",
                        help="Set cluster to operate in", required=True)
    parser.add_argument("--disk_size", dest="disk_size",
                        help="Size of the second (database) disk, in B",
                        default=5000000000, type=int)
    parser.add_argument("--disk_format", dest="disk_format",
                        help="Format of the second (database) disk", default="cow")
    parser.add_argument("--disk_interface", dest="disk_interface",
                        help="Interface of second (database) disk", default="VirtIO")
    parser.add_argument("--provider", dest="provider",
                        help="Rhevm provider (to look for in cfme_data)", default="rhevm32")
    args = parser.parse_args()
    return args


def make_ssh_client(rhevip, sshname, sshpass):
    connect_kwargs = {
        'username': sshname,
        'password': sshpass,
        'hostname': rhevip
    }
    return SSHClient(**connect_kwargs)


def get_ova_name(ovaurl):
    return ovaurl.split("/")[-1]


def download_ova(ssh_client, ovaurl):
    command = 'curl -O %s' % ovaurl
    exit_status, output = ssh_client.run_command(command)
    if exit_status != 0:
        print "RHEVM: There was an error while downloading ova file:"
        print output
        sys.exit(127)


def template_from_ova(api, username, password, rhevip, edomain, ovaname, ssh_client):
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
    #Check if the template is really there
    if not api.templates.get(TEMP_TMP_NAME):
        print "RHEVM: The template failed to import"
        sys.exit(127)


def make_vm_from_template(api, cluster):
    if api.vms.get(TEMP_VM_NAME) is not None:
        print "RHEVM: Warning: found another VM with this name."
        print "RHEVM: Skipping this step, attempting to continue..."
        return
    actual_template = api.templates.get(TEMP_TMP_NAME)
    actual_cluster = api.clusters.get(cluster)
    params_vm = params.VM(name=TEMP_VM_NAME, template=actual_template, cluster=actual_cluster)
    api.vms.add(params_vm)

    #we must wait for the vm do become available
    def check_status():
        status = api.vms.get(TEMP_VM_NAME).get_status()
        if status.state != 'down':
            return False
        return True

    wait_for(check_status, fail_condition=False, delay=5)

    #check, if the vm is really there
    if not api.vms.get(TEMP_VM_NAME):
        print "RHEVM: VM could not be provisioned"
        sys.exit(127)


def check_disks(api):
    disks = api.vms.get(TEMP_VM_NAME).disks.list()
    for disk in disks:
        if disk.get_status().state != "ok":
            return False
    return True


#sometimes, rhevm is just not cooperative. This is function used to wait for template on
#export domain to become unlocked
def check_edomain_template(api, edomain):
    template = api.storagedomains.get(edomain).templates.get(TEMP_TMP_NAME)
    if template.get_status().state != "ok":
        return False
    return True


def add_disk_to_vm(api, sdomain, disk_size, disk_format, disk_interface):
    if len(api.vms.get(TEMP_VM_NAME).disks.list()) > 1:
        print "RHEVM: Warning: found more than one disk in existing VM."
        print "RHEVM: Skipping this step, attempting to continue..."
        return
    actual_sdomain = api.storagedomains.get(sdomain)
    temp_vm = api.vms.get(TEMP_VM_NAME)
    params_disk = params.Disk(storage_domain=actual_sdomain, size=disk_size,
                              interface=disk_interface, format=disk_format)
    temp_vm.disks.add(params_disk)

    wait_for(check_disks, [api], fail_condition=False, delay=5, num_sec=600)

    #check, if there are two disks
    if len(api.vms.get(TEMP_VM_NAME).disks.list()) < 2:
        print "RHEVM: Disk failed to add"
        sys.exit(127)


def templatize_vm(api, template_name, cluster):
    if api.templates.get(template_name) is not None:
        print "RHEVM: Warning: found finished template with this name."
        print "RHEVM: Skipping this step, attempting to continue..."
        return
    temporary_vm = api.vms.get(TEMP_VM_NAME)
    actual_cluster = api.clusters.get(cluster)
    new_template = params.Template(name=template_name, vm=temporary_vm, cluster=actual_cluster)
    api.templates.add(new_template)

    wait_for(check_disks, [api], fail_condition=False, delay=5)

    #check, if template is really there
    if not api.templates.get(template_name):
        print "RHEVM: VM failed to templatize"
        sys.exit(127)


def cleanup(api, edomain):
    temporary_vm = api.vms.get(TEMP_VM_NAME)
    if temporary_vm is not None:
        temporary_vm.delete()
    temporary_template = api.templates.get(TEMP_TMP_NAME)
    if temporary_template is not None:
        temporary_template.delete()

    #waiting for template on export domain
    wait_for(check_edomain_template, [api, edomain], fail_condition=False, delay=5)

    unimported_template = api.storagedomains.get(edomain).templates.get(TEMP_TMP_NAME)
    if unimported_template is not None:
        unimported_template.delete()


def run(**kwargs):
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
        template_name = cfme_data['basic_info']['cfme_template_name']

    if api.templates.get(template_name) is not None:
        print "RHEVM: Found finished template with this name."
        print "RHEVM: The script will now end."
    else:
        print "RHEVM: Downloading .ova file..."
        download_ova(ssh_client, kwargs.get('image_url'))
        print "RHEVM: Templatizing .ova file..."
        template_from_ova(api, username, password, rhevip, kwargs.get('edomain'),
                          ovaname, ssh_client)
        print "RHEVM: Importing new template..."
        import_template(api, kwargs.get('edomain'), kwargs.get('sdomain'), kwargs.get('cluster'))
        print "RHEVM: Making a temporary VM from new template..."
        make_vm_from_template(api, kwargs.get('cluster'))
        print "RHEVM: Adding disk to created VM..."
        add_disk_to_vm(api, kwargs.get('sdomain'), kwargs.get('disk_size'),
                       kwargs.get('disk_format'), kwargs.get('disk_interface'))
        print "RHEVM: Templatizing VM..."
        templatize_vm(api, template_name, kwargs.get('cluster'))
        print "RHEVM: Cleaning up..."
        cleanup(api, kwargs.get('edomain'))

    ssh_client.close()
    api.disconnect()
    print "RHEVM: Done."


if __name__ == "__main__":
    args = parse_cmd_line()

    kwargs = dict(args._get_kwargs())

    run(**kwargs)
