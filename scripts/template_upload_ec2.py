#!/usr/bin/env python2

"""This script takes various parameters specified in
cfme_data['template_upload']['template_upload_ec2'] and/or by command-line arguments.
Parameters specified by command-line have higher priority, and override data in cfme_data.

This script is designed to run either as a standalone ec2 template uploader, or it can be used
together with template_upload_all script. This is why all the function calls, which would
normally be placed in main function, are located in function run(**kwargs).
"""

import argparse
import re
import sys
import os
import urllib2
from threading import Lock

from mgmtsystem import EC2System
from utils.conf import cfme_data
from utils.conf import credentials
from utils.providers import list_provider_keys
from utils.ssh import SSHClient
from utils.wait import wait_for

lock = Lock()


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument("--image_url", dest="image_url",
                        help="URL of vhd image to upload to ec2", default=None)
    parser.add_argument("--template_name", dest="template_name",
                        help="Name of final image on ec2", default=None)
    parser.add_argument("--provider", dest="provider",
                        help="Provider of ec2 service", default=None)
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


def make_ssh_client(rhevip, sshname, sshpass):
    connect_kwargs = {
        'username': sshname,
        'password': sshpass,
        'hostname': rhevip
    }
    return SSHClient(**connect_kwargs)


def download_image_file(image_url, destination=None):
    """Downloads the image on local machine.

        Args:
            image_url: image_url to download the image.
        Returns:
            file_name: downloaded filename.
            file_path: absolute path of the downloaded file.
    """
    file_name = image_url.split('/')[-1]
    u = urllib2.urlopen(image_url)
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    file_path = os.path.abspath(file_name)
    if os.path.isfile(file_name):
        if file_size == os.path.getsize(file_name):
            return file_name, file_path
        os.remove(file_name)
    print("Downloading: {} Bytes: {}".format(file_name, file_size))
    f = open(file_name, 'wb')
    os.system('cls')
    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer_f = u.read(block_sz)
        if not buffer_f:
            break

        file_size_dl += len(buffer_f)
        f.write(buffer_f)
    f.close()
    return file_name, file_path


def create_image(template_name, image_description, bucket_name, key_name):
    """Imports the Image file uploaded to bucket inside amazon s3, checks the image status.
       Waits for import_image task to complete. creates name tag and assigns template_name to
       imported image.

        Args:
            template_name: Name of the template, this will be assigned to Name tag of the
            imported image.
            image_description: description to be set to imported image.
            bucket_name: bucket_name from where image file is imported. This is created in Amazon S3
            service.
            key_name: Keyname inside the create bucket.
    """
    temp_up = cfme_data['template_upload']['template_upload_ec2']
    aws_cli_tool_client_username = credentials['host_default']['username']
    aws_cli_tool_client_password = credentials['host_default']['password']
    sshclient = make_ssh_client(temp_up['aws_cli_tool_client'], aws_cli_tool_client_username,
                                aws_cli_tool_client_password)

    print("AMAZON EC2: Creating JSON file beofre importing the image ...")
    upload_json = """[
  {{
    "Description": "{description}",
    "Format": "vhd",
    "UserBucket": {{
        "S3Bucket": "{bucket_name}",
        "S3Key": "{key_name}"
    }}
}}]""".format(description=image_description, bucket_name=bucket_name,
              key_name=key_name)
    command = '''cat <<EOT > import_image.json
    {}
    '''.format(upload_json)
    sshclient.run_command(command)

    print("AMAZON EC2: Running import-image command and grep ImportTaskId ...")
    command = "aws ec2 import-image --description 'test_cfme_ami_image_upload' --disk-containers " \
              "file://import_image.json | grep ImportTaskId"
    output = sshclient.run_command(command)
    importtask_id = re.findall(r'import-ami-[a-zA-Z0-9_]*', str(output))[0]

    def check_import_task_status():
        check_status_command = "aws ec2 describe-import-image-tasks --import-task-ids {} | grep " \
                               "-w Status".format(importtask_id)
        import_status_output = sshclient.run_command(check_status_command)
        return True if 'completed' in import_status_output else False

    print("AMAZON EC2: Waiting for import-image task to be completed, this may take a while ...")
    wait_for(check_import_task_status, fail_condition=False, delay=5, timeout='1h')

    print("AMAZON EC2: Retrieve AMI ImageId from describe-import-image-tasks...")
    command = "aws ec2 describe-import-image-tasks --import-task-ids {} | grep ImageId".format(
        importtask_id)
    output = sshclient.run_command(command)
    ami_image_id = re.findall(r'ami-[a-zA-Z0-9_]*', str(output))[0]

    print("AMAZON EC2: Creating Tag for imported image ...")
    command = "aws ec2 create-tags --resources {} --tags Key='Name'," \
              "Value='{}'".format(ami_image_id, template_name)
    sshclient.run_command(command)


def upload_template(provider, username, password, upload_bucket_name,
                    image_url, template_name):
    """Downloads the image file from image_url. Creats the bucket in amazon s3 and uploads
       downloaded image file to it. Invokes the create_image method to complete the AMI image import
       process.
       Waits for import_image task to complete. creates name tag and assigns template_name to
         Args:
             provider: provider_key under execution.
             username: Amazon console username(Access_Id).
             password: Amazon console password(Access_key).
             upload_bucket_name: bucket_name to upload the image. bucket is created in Amazon S3
             service.
             image_url: Image_url to download the image file.
             template_name: name of the template to assign to the imported image.
     """
    try:
        print("AMAZON EC2:{} Starting image download {} ...".format(provider, image_url))
        file_name, file_path = download_image_file(image_url)
        print("AMAZON EC2:{} Image downloaded {} ...".format(provider, file_path))
        kwargs = {
            'username': username,
            'password': password
        }
        ec2 = EC2System(**kwargs)
        print("AMAZON EC2:{} Creating bucket {}...".format(provider, upload_bucket_name))
        ec2.create_s3_bucket(upload_bucket_name)
        print("AMAZON EC2:{} uploading file to bucket {}...".format(provider, upload_bucket_name))
        ec2.upload_file_to_s3_bucket(upload_bucket_name, file_path=file_path,
                                     key_name=template_name)
        print("AMAZON EC2:{} File uploading done ...".format(provider))

        print("AMAZON EC2:{} Creating ami template/image {}...".format(provider, template_name))
        create_image(template_name, image_description=template_name, bucket_name=upload_bucket_name,
                     key_name=template_name)
        print("AMAZON EC2:{} Successfully uploaded the template.".format(provider))
    except Exception as e:
        print(e)
        print("AMAZON EC2:{} Error occurred in upload_template".format(provider))
        return False
    finally:
        print("AMAZON EC2:{} End template {} upload...".format(provider, template_name))


def run(**kwargs):
    """Calls all the functions needed to import new template to EC2.
        This is called either by template_upload_all script, or by main function.

     Args:
         **kwargs: Kwargs are passed by template_upload_all.
     """
    mgmt_sys = cfme_data['management_systems']
    for provider in list_provider_keys('ec2'):
        ssh_rhevm_creds = mgmt_sys[provider]['credentials']
        username = credentials[ssh_rhevm_creds]['username']
        password = credentials[ssh_rhevm_creds]['password']
        upload_bucket_name = mgmt_sys[provider]['upload_bucket_name']
        upload_template(provider, username, password, upload_bucket_name, kwargs.get(
            'image_url'), kwargs.get('template_name'))


if __name__ == '__main__':
    args = parse_cmd_line()
    kwargs = cfme_data['template_upload']['template_upload_ec2']
    final_kwargs = make_kwargs(args, **kwargs)

    run(**final_kwargs)
