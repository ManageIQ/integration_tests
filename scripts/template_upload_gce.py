#!/usr/bin/env python2

"""This script takes various parameters specified in
cfme_data['template_upload']['template_upload_gce'] and/or by command-line arguments.
Parameters specified by command-line have higher priority, and override data in cfme_data.

This script is designed to run either as a standalone gce template uploader, or it can be used
together with template_upload_all script. This is why all the function calls, which would
normally be placed in main function, are located in function run(**kwargs).
"""

import argparse
import re
import sys
from threading import Lock, Thread
from datetime import datetime

from utils.conf import cfme_data
from utils.conf import credentials
from utils.ssh import SSHClient
from utils.providers import list_provider_keys

lock = Lock()


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument("--image_url", dest="image_url",
                        help="URL of .tar.gz image to upload to gce", default=None)
    parser.add_argument("--template_name", dest="template_name",
                        help="Name of final image on gce", default=None)
    parser.add_argument("--provider", dest="provider",
                        help="Provider of GCE service", default=None)
    args = parser.parse_args()
    return args


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


def make_ssh_client(hostname=None, sshname=None, sshpass=None):
    # Defaults connect to the cli tool client
    if hostname is None:
        hostname = cfme_data['template_upload']['template_upload_ec2']['aws_cli_tool_client']
    if sshname is None:
        sshname = credentials['host_default']['username']
    if sshpass is None:
        sshpass = credentials['host_default']['password']

    connect_kwargs = {
        'username': sshname,
        'password': sshpass,
        'hostname': hostname
    }
    return SSHClient(**connect_kwargs)


def log_detail(message, provider=None):
    if provider:
        print("{} GCE: {}: {}".format(datetime.utcnow(), provider, message))
    else:
        print("{} INFO: {}".format(datetime.utcnow(), message))


def download_image_file(image_url):
    """
    Download the file to the cli-tool-client and return the file path + file name
    Default destinations are None and are set to the cli-tool-client if left that way
    :param image_url: string url to the tar.gz image
    :return: tuple: file_name, file_path strings
    """
    # TODO: add a --local option to the script and run commands locally to download
    # Download to the amazon/gce upload machine in the lab because its fast
    target_dir = '/root/downloads'
    file_name = image_url.split('/')[-1]
    with make_ssh_client() as ssh_client:
        # check if file exists
        print('INFO: Checking if file exists on cli-tool-client...')
        result = ssh_client.run_command('ls -1 {}/{}'.format(target_dir, file_name))
        if result.success:
            print('INFO: File exists on cli-tool-client, skipping download...')
            return file_name, target_dir

        # target directory setup
        print('INFO: Prepping cli-tool-client machine for download...')
        assert ssh_client.run_command('mkdir -p {}'.format(target_dir))
        # This should keep the downloads directory clean
        assert ssh_client.run_command('rm -f {}/*.gz'.format(target_dir))

        # get the file
        download_cmd = 'cd {}; ' \
                       'curl -O {}'.format(target_dir, image_url)
        print('INFO: Downloading file to cli-tool-client with command: {}'.format(download_cmd))
        assert ssh_client.run_command(download_cmd)
        print('INFO: Download finished...')

    return file_name, target_dir


def check_template_name(name):
    pattern = re.compile("(?:[a-z](?:[-a-z0-9]{0,61}[a-z0-9])?)")
    match = pattern.match(name)
    if isinstance(match.group(), str) and match.group() != name:
        name = cfme_data['basic_info']['appliance_template']
    return name


def upload_template(provider, template_name, file_name, file_path, bucket_name=None):
    bucket = bucket_name or cfme_data['template_upload']['template_upload_gce']['bucket_name']
    try:
        with make_ssh_client() as ssh_client:
            log_detail('Checking if template {} present...'.format(template_name), provider)
            result = ssh_client.run_command('gcloud compute images list {}'.format(template_name))
            if 'Listed 0 items' not in result.output:
                log_detail('Image {} already present in GCE, stopping upload'.format(template_name),
                           provider)
                return True
            log_detail('Image NOT {} present, continuing upload'.format(template_name), provider)
            log_detail('Creating bucket {}...'.format(bucket))
            # gsutil has RC 1 and a API 409 in stdout if bucket exists
            result = ssh_client.run_command('gsutil mb gs://{}'.format(bucket))
            assert result or 'already exists' in result

            log_detail('Checking if file on bucket already...')
            result = ssh_client.run_command('gsutil ls gs://{}/{}'.format(bucket, file_name))
            if result.failed:
                # file not found, upload
                log_detail('Uploading to bucket...')
                result = ssh_client.run_command(
                    'gsutil cp {}/{} gs://{}'.format(file_path, file_name, bucket))
                assert result.success
                log_detail('File uploading done ...')
            else:
                log_detail('File already on bucket...')

            log_detail('Creating template {}...'.format(template_name), provider)
            template_name = check_template_name(template_name)
            image_cmd = 'gcloud compute images create {} --source-uri gs://{}/{}'\
                .format(template_name, bucket, file_name)
            result = ssh_client.run_command(image_cmd)
            assert result.success
        log_detail('Successfully added template {} from bucket {}'.format(template_name, bucket),
                   provider)

        log_detail('Cleaning up, removing {} from bucket {}...'.format(file_name, bucket), provider)
        result = ssh_client.run_command('gsutil rm gs://{}/{}'.format(bucket, file_name))
        assert result.success
    except Exception as e:
        print(e)
        # exception often empty, try to include last ssh command output
        log_detail('Error occurred in upload_template: \n {}'.format(result.output), provider)
        return False
    finally:
        log_detail('End template {} upload...'.format(template_name), provider)
        return True


def run(**kwargs):
    # Download file once and thread uploading to different gce regions
    file_name, file_path = download_image_file(kwargs.get('image_url'))

    thread_queue = []
    for provider in list_provider_keys("gce"):
        template_name = kwargs.get('template_name')
        bucket_name = kwargs.get('bucket_name')
        thread = Thread(target=upload_template,
                        args=(provider,
                              template_name,
                              file_name,
                              file_path,
                              bucket_name))
        thread.daemon = True
        thread_queue.append(thread)
        thread.start()

    for thread in thread_queue:
        thread.join()


if __name__ == '__main__':
    args = parse_cmd_line()
    kwargs = cfme_data['template_upload']['template_upload_gce']
    final_kwargs = make_kwargs(args, **kwargs)

    run(**final_kwargs)
