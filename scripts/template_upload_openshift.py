#!/usr/bin/env python2

"""This script takes various parameters specified in
cfme_data['template_upload']['template_upload_openshift'] and/or by command-line arguments.
Parameters specified by command-line have higher priority, and override data in cfme_data.

This script is designed to run either as a standalone openshift template uploader, or it can be used
together with template_upload_all script. This is why all the function calls, which would
normally be placed in main function, are located in function run(**kwargs).
"""

import argparse
import os
from threading import Lock, Thread

from cfme.utils import net, trackerbot
from cfme.utils.conf import cfme_data, credentials
from cfme.utils.log import logger, add_stdout_handler
from cfme.utils.providers import list_provider_keys
from cfme.utils.ssh import SSHClient

lock = Lock()

add_stdout_handler(logger)


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--image_url', metavar='URL', dest="image_url",
                        help="URL of OVA", default=None)
    parser.add_argument('--template_name', dest="template_name",
                        help="Override/Provide name of template", default=None)
    args = parser.parse_args()
    return args


def check_kwargs(**kwargs):
    for key, val in kwargs.iteritems():
        if val is None:
            logger.error("OPENSHIFT:%r Supply required parameter '%r'", kwargs['provider'], key)
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


def list_templates(hostname, username, password, upload_folder):
    with SSHClient(hostname=hostname, username=username, password=password) as ssh:
        cmd = 'find {u}/* -maxdepth 1 -type d -exec basename {{}} \;'.format(u=upload_folder)
        result = ssh.run_command(cmd)
        if result.success and len(str(result)) > 0:
            return str(result).split()
        else:
            return []


def upload_template(hostname, username, password,
                    provider, url, name, provider_data, stream, upload_folder):
    try:
        kwargs = {}

        if name is None:
            name = cfme_data['basic_info']['appliance_template']

        logger.info("OPENSHIFT:%r Start uploading Template: %r", provider, name)
        if not check_kwargs(**kwargs):
            return False

        if name not in list_templates(hostname, username, password, upload_folder):
            with SSHClient(hostname=hostname, username=username, password=password) as ssh:
                dest_dir = os.path.join(upload_folder, name)
                result = ssh.run_command('mkdir {dir}'.format(dir=dest_dir))
                if result.failed:
                    logger.exception("OPENSHIFT: cant create folder %r", str(result))
                    raise
                download_cmd = ('wget -q --no-parent --no-directories --reject "index.html*" '
                                '--directory-prefix={dir} -r {url}')
                result = ssh.run_command(download_cmd.format(dir=dest_dir, url=url))
                if result.failed:
                    logger.exception("OPENSHIFT: cannot upload template %r", str(result))
                    raise

            if not provider_data:
                logger.info("OPENSHIFT:%r Adding template %r to trackerbot", provider, name)
                trackerbot.trackerbot_add_provider_template(stream, provider, name)
        else:
            logger.info("OPENSHIFT:%r template %r already exists", provider, name)

    except Exception:
        logger.exception('OPENSHIFT:%r Exception during upload_template', provider)
        return False
    finally:
        logger.info("OPENSHIFT:%r End uploading Template: %r", provider, name)


def run(**kwargs):

    try:
        thread_queue = []
        providers = list_provider_keys("openshift")
        if kwargs['provider_data']:
            mgmt_sys = providers = kwargs['provider_data']['management_systems']
        else:
            mgmt_sys = cfme_data['management_systems']
        for provider in providers:
            if 'podtesting' not in mgmt_sys[provider]['tags']:
                continue
            if kwargs['provider_data']:
                username = mgmt_sys[provider]['username']
                password = mgmt_sys[provider]['password']
            else:
                creds = credentials[mgmt_sys[provider]['ssh_creds']]
                username = creds['username']
                password = creds['password']
            host_ip = mgmt_sys[provider]['ipaddress']
            hostname = mgmt_sys[provider]['hostname']

            upload_parameters = cfme_data['template_upload']['template_upload_openshift']
            upload_folder = kwargs.get('upload_folder', upload_parameters['upload_folder'])

            if not net.is_pingable(host_ip):
                continue
            thread = Thread(target=upload_template,
                            args=(hostname, username, password, provider,
                                  kwargs.get('image_url'), kwargs.get('template_name'),
                                  kwargs['provider_data'], kwargs['stream'], upload_folder))
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

    kwargs = cfme_data['template_upload']['template_upload_openshift']

    final_kwargs = make_kwargs(args, **kwargs)

    run(**final_kwargs)
