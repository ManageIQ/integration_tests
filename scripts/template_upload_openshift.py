#!/usr/bin/env python2

"""This script takes various parameters specified in
cfme_data['template_upload']['template_upload_openshift'] and/or by command-line arguments.
Parameters specified by command-line have higher priority, and override data in cfme_data.

This script is designed to run either as a standalone openshift template uploader, or it can be used
together with template_upload_all script. This is why all the function calls, which would
normally be placed in main function, are located in function run(**kwargs).
"""

import argparse
import inspect
import os
from threading import Lock, Thread

from cfme.utils import net, trackerbot
from cfme.utils.conf import cfme_data, credentials
from cfme.utils.log import logger, add_stdout_handler
from cfme.utils.providers import list_provider_keys
from cfme.utils.ssh import SSHClient

lock = Lock()
add_stdout_handler(logger)
cur_dir = os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--image_url', metavar='URL', dest="image_url",
                        help="URL of OVA", default=None)
    parser.add_argument('--template_name', dest="template_name",
                        help="Override/Provide name of template", default=None)
    args = parser.parse_args()
    return args


def check_kwargs(**kwargs):
    for key, val in kwargs.items():
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


def list_templates(hostname, username, password, upload_folder):
    with SSHClient(hostname=hostname, username=username, password=password) as ssh:
        cmd = 'find {u}/* -maxdepth 1 -type d -exec basename {{}} \;'.format(u=upload_folder)
        result = ssh.run_command(cmd)
        if result.success and len(str(result)) > 0:
            return str(result).split()
        else:
            return []


def upload_template(hostname, username, password, provider, url, name, provider_data,
                    stream, upload_folder, oc_username, oc_password):
    try:
        kwargs = {}

        if name is None:
            name = cfme_data['basic_info']['appliance_template']

        logger.info("OPENSHIFT:%r Start uploading Template: %r", provider, name)
        if not check_kwargs(**kwargs):
            return False

        logger.info("checking whether this template is already present in provider env")
        if name not in list_templates(hostname, username, password, upload_folder):
            with SSHClient(hostname=hostname, username=username, password=password) as ssh:
                # creating folder to store template files
                dest_dir = os.path.join(upload_folder, name)
                logger.info("creating folder for templates: {f}".format(f=dest_dir))
                result = ssh.run_command('mkdir {dir}'.format(dir=dest_dir))
                if result.failed:
                    err_text = "OPENSHIFT: cant create folder {}".format(str(result))
                    logger.exception(err_text)
                    raise RuntimeError(err_text)
                download_cmd = ('wget -q --no-parent --no-directories --reject "index.html*" '
                                '--directory-prefix={dir} -r {url}')
                logger.info("downloading templates to destination dir {f}".format(f=dest_dir))
                result = ssh.run_command(download_cmd.format(dir=dest_dir, url=url))
                if result.failed:
                    err_text = "OPENSHIFT: cannot download template {}".format(str(result))
                    logger.exception(err_text)
                    raise RuntimeError(err_text)

                # updating image streams in openshift
                logger.info("logging in to openshift")
                login_cmd = 'oc login --username={u} --password={p}'
                result = ssh.run_command(login_cmd.format(u=oc_username, p=oc_password))
                if result.failed:
                    err_text = "OPENSHIFT: couldn't login to openshift {}".format(str(result))
                    logger.exception(err_text)
                    raise RuntimeError(err_text)

                logger.info("looking for templates in destination dir {f}".format(f=dest_dir))
                get_urls_cmd = 'find {d} -type f -name "cfme-openshift-*" -exec tail -1 {{}} \;'
                result = ssh.run_command(get_urls_cmd.format(d=dest_dir))
                if result.failed:
                    err_text = "OPENSHIFT: couldn't get img stream urls {}".format(str(result))
                    logger.exception(err_text)
                    raise RuntimeError(err_text)

                tags = {}
                for img_url in str(result).split():
                    update_img_cmd = 'docker pull {url}'
                    logger.info("updating image stream to tag {t}".format(t=img_url))
                    result = ssh.run_command(update_img_cmd.format(url=img_url))
                    # url ex:
                    # brew-pulp-docker01.web.prod.ext.phx2.redhat.com:8888/cloudforms46/cfme-openshift-httpd:2.4.6-14
                    tag_name, tag_value = img_url.split('/')[-1].split(':')
                    tag_url = img_url.rpartition(':')[-1]
                    tags[tag_name] = {'tag': tag_value, 'url': tag_url}
                    if result.failed:
                        err_text = ("OPENSHIFT: couldn't update image stream using url "
                                    "{}, {}".format(img_url, str(result)))
                        logger.exception(err_text)
                        raise RuntimeError(err_text)

                logger.info('updating templates before upload to openshift')
                # updating main template file, adding essential patches
                main_template_file = 'cfme-template.yaml'
                main_template = os.path.join(dest_dir, main_template_file)

                default_template_name = 'cloudforms'
                new_template_name = name
                logger.info('removing old templates from ocp if those exist')
                for template in (default_template_name, new_template_name):
                    if ssh.run_command('oc get template {t} '
                                       '--namespace=openshift'.format(t=template)).success:
                        ssh.run_command('oc delete template {t} '
                                        '--namespace=openshift'.format(t=template))

                logger.info('changing template name to unique one')
                change_name_cmd = """python -c 'import yaml
data = yaml.safe_load(open("{file}"))
data["metadata"]["name"] = "{new_name}"
yaml.safe_dump(data, stream=open("{file}", "w"))'""".format(new_name=new_template_name,
                                                            file=main_template)
                # our templates always have the same name but we have to keep many templates
                # of the same stream. So we have to change template name before upload to ocp
                # in addition, openshift doesn't provide any convenient way to change template name
                logger.info(change_name_cmd)
                result = ssh.run_command(change_name_cmd)
                if result.failed:
                    err_text = "OPENSHIFT: couldn't change default template name"
                    logger.exception(err_text)
                    raise RuntimeError(err_text)

                logger.info("uploading main template to ocp")
                result = ssh.run_command('oc create -f {t} '
                                         '--namespace=openshift'.format(t=main_template))
                if result.failed:
                    err_text = "OPENSHIFT: couldn't upload template to openshift"
                    logger.exception(err_text)
                    raise RuntimeError(err_text)

            if not provider_data:
                logger.info("OPENSHIFT:%r Adding template %r to trackerbot", provider, name)
                trackerbot.trackerbot_add_provider_template(stream=stream,
                                                            provider=provider,
                                                            template_name=name,
                                                            custom_data={'TAGS': tags})

            logger.info("upload has been finished successfully")
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
            # skip provider if block_upload is set
            if (mgmt_sys[provider].get('template_upload') and
                    mgmt_sys[provider]['template_upload'].get('block_upload')):
                logger.info('Skipping upload on {} due to block_upload'.format(provider))
                continue
            if 'podtesting' not in mgmt_sys[provider]['tags']:
                continue
            if kwargs['provider_data']:
                username = mgmt_sys[provider]['username']
                password = mgmt_sys[provider]['password']
            else:
                ssh_creds = credentials[mgmt_sys[provider]['ssh_creds']]
                username = ssh_creds['username']
                password = ssh_creds['password']
                oc_creds = credentials[mgmt_sys[provider]['credentials']]
                oc_username = oc_creds['username']
                oc_password = oc_creds['password']
            host_ip = mgmt_sys[provider]['ipaddress']
            hostname = mgmt_sys[provider]['hostname']

            upload_parameters = cfme_data['template_upload']['template_upload_openshift']
            upload_folder = kwargs.get('upload_folder', upload_parameters['upload_folder'])

            if not net.is_pingable(host_ip):
                continue
            thread = Thread(target=upload_template,
                            args=(hostname, username, password, provider,
                                  kwargs.get('image_url'), kwargs.get('template_name'),
                                  kwargs['provider_data'], kwargs['stream'], upload_folder,
                                  oc_username, oc_password))
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
