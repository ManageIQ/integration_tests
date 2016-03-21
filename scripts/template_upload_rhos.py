#!/usr/bin/env python2

"""This script takes various parameters specified in
cfme_data['template_upload']['template_upload_rhos'] and/or by command-line arguments.
Parameters specified by command-line have higher priority, and override data in cfme_data.

This script is designed to run either as a standalone rhos template uploader, or it can be used
together with template_upload_all script. This is why all the function calls, which would
normally be placed in main function, are located in function run(**kwargs).
"""

import argparse
import sys

from utils.conf import cfme_data
from utils.conf import credentials
from utils.ssh import SSHClient
from utils.wait import wait_for


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument("--tenant_id", dest="tenant_id",
                        help="Tenand ID for selected user", default=None)
    parser.add_argument("--image_url", dest="image_url",
                        help="URL of .qc2 image to upload to openstack", default=None)
    parser.add_argument("--template_name", dest="template_name",
                        help="Name of final image on openstack", default=None)
    parser.add_argument("--provider", dest="provider",
                        help="Provider of RHOS service", default=None)
    args = parser.parse_args()
    return args


def make_ssh_client(rhosip, sshname, sshpass):
    connect_kwargs = {
        'username': sshname,
        'password': sshpass,
        'hostname': rhosip
    }
    return SSHClient(**connect_kwargs)


def make_export(username, password, tenant_id, auth_url):
    export = ['export']
    export.append("OS_USERNAME={}".format(username))
    export.append("OS_PASSWORD={}".format(password))
    export.append("OS_TENANT_ID={}".format(tenant_id))
    export.append("OS_AUTH_URL={}".format(auth_url))
    return ' '.join(export)


def upload_qc2_file(ssh_client, image_url, template_name, export):
    command = ['glance']
    command.append("image-create")
    command.append("--copy-from {}".format(image_url))
    command.append("--name {}".format(template_name))
    command.append("--is-public true")
    command.append("--container-format bare")
    command.append("--disk-format qcow2")

    res_command = ' '.join(command)
    res = '{} && {}'.format(export, res_command)
    exit_status, output = ssh_client.run_command(res)

    if exit_status != 0:
        print("RHOS: There was an error while uploading qc2 file.")
        print(output)
        sys.exit(127)

    return output


def get_image_id(glance_output):
    first_index = glance_output.find('|', glance_output.find('id')) + 1
    second_index = glance_output.find('|', first_index)
    image_id = glance_output[first_index:second_index].replace(' ', '')
    return image_id


def get_image_status(glance_output):
    first_index = glance_output.find('|', glance_output.find('status')) + 1
    second_index = glance_output.find('|', first_index)
    image_status = glance_output[first_index:second_index].replace(' ', '')
    return image_status


def check_image_status(image_id, export, ssh_client):
    command = ['glance']
    command.append('image-show {}'.format(image_id))

    res = ' '.join(command)

    exit_status, output = ssh_client.run_command('{} && {}'.format(export, res))

    if exit_status != 0:
        print("RHOS: There was an error while checking status of image.")
        print(output)
        sys.exit(127)

    if get_image_status(output) != 'active':
        return False
    return True


def check_image_exists(image_name, export, ssh_client):
    command = ['glance']
    command.append('image-list')
    command.append('|')
    command.append('grep {}'.format(image_name))

    res_command = ' '.join(command)
    res = '{} && {}'.format(export, res_command)
    exit_status, output = ssh_client.run_command(res)

    if output:
        return True
    return False


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

    for key, val in kwargs.iteritems():
        if val is None:
            print("ERROR: please supply required parameter '{}'.".format(key))
            sys.exit(127)

    return kwargs


def run(**kwargs):
    mgmt_sys = cfme_data['management_systems'][kwargs.get('provider')]
    rhos_credentials = credentials[mgmt_sys['credentials']]
    default_host_creds = credentials['host_default']

    username = rhos_credentials['username']
    password = rhos_credentials['password']
    auth_url = mgmt_sys['auth_url']
    rhosip = mgmt_sys['ipaddress']
    sshname = default_host_creds['username']
    sshpass = default_host_creds['password']

    print("RHOS: Starting rhos upload...")

    ssh_client = make_ssh_client(rhosip, sshname, sshpass)

    template_name = kwargs.get('template_name', None)
    if template_name is None:
        template_name = cfme_data['basic_info']['appliance_template']

    export = make_export(username, password, kwargs.get('tenant_id'), auth_url)

    if not check_image_exists(template_name, export, ssh_client):
        output = upload_qc2_file(ssh_client, kwargs.get('image_url'), template_name, export)

        image_id = get_image_id(output)

        wait_for(check_image_status, [image_id, export, ssh_client],
                 fail_condition=False, delay=5, num_sec=300)
    else:
        print("RHOS: Found image with same name. Exiting...")

    ssh_client.close()
    print("RHOS: Done.")


if __name__ == '__main__':
    args = parse_cmd_line()

    kwargs = cfme_data['template_upload']['template_upload_rhos']

    final_kwargs = make_kwargs(args, **kwargs)

    run(**final_kwargs)
