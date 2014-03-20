#!/usr/bin/python

import argparse
import sys

from utils.conf import cfme_data
from utils.conf import credentials
from utils.ssh import SSHClient


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument("--tenant_id", dest="tenant_id",
                        help="Tenand ID for selected user", required=True)
    parser.add_argument("--image_url", dest="image_url",
                        help="URL of .qc2 image to upload to openstack", required=True)
    parser.add_argument("--template_name", dest="template_name",
                        help="Name of final image on openstack", required=True)
    parser.add_argument("--provider", dest="provider",
                        help="Provider of RHOS service", required=True)
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
    export.append("OS_USERNAME=%s" % username)
    export.append("OS_PASSWORD=%s" % password)
    export.append("OS_TENANT_ID=%s" % tenant_id)
    export.append("OS_AUTH_URL=%s" % auth_url)
    return ' '.join(export)


def upload_qc2_file(ssh_client, image_url, template_name, export):
    command = ['glance']
    command.append("image-create")
    command.append("--copy-from %s" % image_url)
    command.append("--name %s" % template_name)
    command.append("--is-public true")
    command.append("--container-format bare")
    command.append("--disk-format qcow2")

    res_command = ' '.join(command)
    res = '%s && %s' % (export, res_command)
    exit_status, output = ssh_client.run_command(res)

    if exit_status != 0:
        print "RHOS: There was an error while uploading qc2 file."
        print output
        sys.exit(127)


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

    print "RHOS: Starting rhos upload..."

    ssh_client = make_ssh_client(rhosip, sshname, sshpass)

    template_name = kwargs.get('template_name', None)
    if template_name is None:
        template_name = cfme_data['basic_info']['cfme_template_name']

    upload_qc2_file(ssh_client, kwargs.get('image_url'), template_name,
                    make_export(username, password, kwargs.get('tenant_id'), auth_url))

    ssh_client.close()
    print "RHOS: Done."


if __name__ == '__main__':
    args = parse_cmd_line()

    kwargs = dict(args._get_kwargs())

    run(**kwargs)
