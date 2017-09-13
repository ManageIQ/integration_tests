#!/usr/bin/env python2

"""This script takes various parameters specified in
cfme_data['template_upload']['template_upload_rhos'] and/or by command-line arguments.
Parameters specified by command-line have higher priority, and override data in cfme_data.

This script is designed to run either as a standalone rhos template uploader, or it can be used
together with template_upload_all script. This is why all the function calls, which would
normally be placed in main function, are located in function run(**kwargs).
"""

import argparse
import fauxfactory
import sys
from threading import Lock, Thread

from cfme.utils import net, ports, trackerbot
from cfme.utils.conf import cfme_data, credentials
from cfme.utils.log import logger, add_stdout_handler
from cfme.utils.providers import list_provider_keys
from cfme.utils.ssh import SSHClient
from cfme.utils.wait import wait_for

lock = Lock()

add_stdout_handler(logger)


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


def upload_qc2_file(ssh_client, image_url, template_name, export, provider):
    try:
        command = ['glance']
        command.append("--os-image-api-version 1")
        command.append("image-create")
        command.append("--copy-from {}".format(image_url))
        command.append("--name {}".format(template_name))
        command.append("--is-public true")
        command.append("--container-format bare")
        command.append("--disk-format qcow2")

        res_command = ' '.join(command)
        res = '{} && {}'.format(export, res_command)
        result = ssh_client.run_command(res)

        if result.failed:
            logger.error("RHOS:%r ERROR while uploading qc2 file: %r", provider, result)
            return False
        return str(result)
    except Exception:
        logger.exception()
        return False


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
    try:
        command = ['glance']
        command.append('image-show {}'.format(image_id))

        res = ' '.join(command)

        result = ssh_client.run_command('{} && {}'.format(export, res))

        if result.failed:
            logger.error("RHOS: There was an error while checking status of image: %r", result)
            return False

        if get_image_status(str(result)) != 'active':
            return False
        return True
    except Exception:
        logger.exception()
        return False


def check_image_exists(image_name, export, ssh_client):
    try:
        command = ['glance']
        command.append('image-list')
        command.append('|')
        command.append('grep {}'.format(image_name))

        res_command = ' '.join(command)
        res = '{} && {}'.format(export, res_command)
        result = ssh_client.run_command(res)

        if result.success:
            return True
        return False
    except Exception:
        logger.exception()
        return False


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

    for key, val in kwargs.iteritems():
        if val is None:
            logger.error("ERROR: please supply required parameter '%r'.", key)
            sys.exit(127)

    return kwargs


def make_kwargs_rhos(cfme_data, provider):
    data = cfme_data['management_systems'][provider]

    if data.get('template_upload'):
        tenant_id = data['template_upload'].get('tenant_id')
    else:
        tenant_id = None

    kwargs = {'provider': provider}
    if tenant_id:
        kwargs['tenant_id'] = tenant_id
    return kwargs


def upload_template(rhosip, sshname, sshpass, username, password, auth_url, provider, image_url,
                    template_name, provider_data, stream):
    try:
        logger.info("RHOS:%r Starting template %r upload", provider, template_name)

        if provider_data:
            kwargs = make_kwargs_rhos(provider_data, provider)
        else:
            kwargs = make_kwargs_rhos(cfme_data, provider)

        kwargs['image_url'] = image_url
        if template_name is None:
            template_name = cfme_data['basic_info']['appliance_template']

        export = make_export(username, password, kwargs.get('tenant_id'), auth_url)

        with make_ssh_client(rhosip, sshname, sshpass) as ssh_client:
            if not check_image_exists(template_name, export, ssh_client):
                output = upload_qc2_file(ssh_client,
                                         kwargs.get('image_url'),
                                         template_name,
                                         export,
                                         provider)
                if not output:
                    logger.error("RHOS:%r upload_qc2_file returned None: %r",
                                 provider, template_name)
                else:
                    image_id = get_image_id(output)
                    wait_for(check_image_status, [image_id, export, ssh_client],
                             fail_condition=False, delay=5, num_sec=300)
                    logger.info("RHOS:%r Successfully uploaded the template.", provider)

                    if not provider_data:
                        logger.info("RHOS:%r Adding template %r to trackerbot",
                                    provider, template_name)
                        trackerbot.trackerbot_add_provider_template(stream, provider, template_name)
            else:
                logger.info("RHOS:%r Found image with name %r. Exiting", provider, template_name)
            if provider_data and check_image_exists(template_name, export, ssh_client):
                logger.info("RHOS:%r Deploying Template %r....", provider, template_name)
                vm_name = 'test_{}_{}'.format(template_name, fauxfactory.gen_alphanumeric(8))
                deploy_args = {'provider': provider, 'vm_name': vm_name,
                               'template': template_name, 'deploy': True}
                getattr(__import__('clone_template'), "main")(**deploy_args)
    except Exception:
        logger.exception("RHOS:%r Exception while uploading template", provider)
        return False
    finally:
        logger.info("RHOS:%r End template %r upload", provider, template_name)


def run(**kwargs):

    thread_queue = []
    providers = list_provider_keys("openstack")
    if kwargs['provider_data']:
        provider_data = kwargs['provider_data']
        mgmt_sys = providers = provider_data['management_systems']
    for provider in providers:
        if kwargs['provider_data']:
            if mgmt_sys[provider]['type'] != 'openstack':
                continue
            username = mgmt_sys[provider]['username']
            password = mgmt_sys[provider]['password']
            sshname = mgmt_sys[provider]['sshname']
            sshpass = mgmt_sys[provider]['sshpass']
        else:
            mgmt_sys = cfme_data['management_systems']
            rhos_credentials = credentials[mgmt_sys[provider]['credentials']]
            default_host_creds = credentials['host_default']
            username = rhos_credentials['username']
            password = rhos_credentials['password']
            sshname = default_host_creds['username']
            sshpass = default_host_creds['password']
        rhosip = mgmt_sys[provider]['ipaddress']
        auth_url = mgmt_sys[provider]['auth_url']
        if not net.is_pingable(rhosip):
            continue
        if not net.net_check(ports.SSH, rhosip):
            logger.error("SSH connection to %r:%r failed, port unavailable", provider, ports.SSH)
            continue
        thread = Thread(target=upload_template,
                        args=(rhosip, sshname, sshpass, username, password, auth_url, provider,
                              kwargs.get('image_url'), kwargs.get('template_name'),
                              kwargs['provider_data'], kwargs['stream']))
        thread.daemon = True
        thread_queue.append(thread)
        thread.start()

    for thread in thread_queue:
        thread.join()


if __name__ == '__main__':
    args = parse_cmd_line()

    kwargs = cfme_data['template_upload']['template_upload_rhos']

    final_kwargs = make_kwargs(args, **kwargs)

    run(**final_kwargs)
