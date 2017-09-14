#!/usr/bin/env python2

"""This script takes various parameters specified in
cfme_data['template_upload']['template_upload_ec2'] and/or by command-line arguments.
Parameters specified by command-line have higher priority, and override data in cfme_data.

This script is designed to run either as a standalone ec2 template uploader, or it can be used
together with template_upload_all script. This is why all the function calls, which would
normally be placed in main function, are located in function run(**kwargs).
"""
import argparse
import sys
import os
import urllib2
from threading import Lock

from wrapanapi.exceptions import ImageNotFoundError, MultipleImagesError

from cfme.utils import trackerbot
from cfme.utils.conf import cfme_data
from cfme.utils.log import logger, add_stdout_handler
from cfme.utils.providers import get_mgmt
from cfme.utils.ssh import SSHClient
from cfme.utils.wait import wait_for

lock = Lock()

add_stdout_handler(logger)


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--stream', dest='stream',
                        help='stream name: downstream-##z, upstream, upstream_stable, etc',
                        default=None)
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


def check_for_ami(ec2, ami_name):
    """
    Check if the AMI exists in the given region
    :param ec2: mgmtsystem:EC2System object
    :param ami_name: string ami name to look for
    :return: string id value for ami
    """
    try:
        id = ec2._get_ami_id_by_name(ami_name)
    except ImageNotFoundError:
        return None

    return id


def make_ssh_client(rhevip, sshname, sshpass):
    connect_kwargs = {
        'username': sshname,
        'password': sshpass,
        'hostname': rhevip
    }
    return SSHClient(**connect_kwargs)


def download_image_file(image_url):
    """
    Download the image to the local working directory
    :param image_url: URL of the file to download
    :return: tuple, file name and file path strings
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
    logger.info("Downloading: %r Bytes: %r", file_name, file_size)
    with open(file_name, 'wb') as image_file:
        # os.system('cls')
        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer_f = u.read(block_sz)
            if not buffer_f:
                break

            file_size_dl += len(buffer_f)
            image_file.write(buffer_f)
    return file_name, file_path


def create_image(ec2, ami_name, bucket_name):
    """
    Create the image from a given bucket+file defined by the ami_name
    :param ec2: mgmtsystem:EC2System object
    :param ami_name: name of the file in the bucket, will be used for AMI name too
    :param bucket_name: name of the s3 bucket where the image is
    :return: none
    """
    logger.info('EC2:%r: Adding image %r from bucket %r...', ec2.api.region, ami_name, bucket_name)
    import_task_id = ec2.import_image(
        s3bucket=bucket_name, s3key=ami_name, description=ami_name)

    logger.info('EC2:%r: Monitoring image task id %r...', ec2.api.region, import_task_id)
    wait_for(ec2.get_image_id_if_import_completed,
             func_args=[import_task_id],
             fail_condition=False,
             delay=5,
             timeout='30m',
             message='Importing image to EC2')

    ami_id = ec2.get_image_id_if_import_completed(import_task_id)

    logger.info("EC2:%r: Copying image to set 'name' attribute %r...", ec2.api.region, ami_name)
    ec2.copy_image(source_region=ec2.api.region.name, source_image=ami_id, image_id=ami_name)

    logger.info("EC2:%r: Removing original un-named imported image %r...", ec2.api.region, ami_id)
    ec2.deregister_image(image_id=ami_id)


def upload_to_s3(ec2, bucket_name, ami_name, file_path):
    """
    Create a bucket and upload the given file to the bucket
    :param ec2: mgmtsystem:EC2System object
    :param bucket_name: string name of bucket to create/upload to
    :param ami_name: string name of the file in the bucket
    :param file_path: string path to the local file to upload
    :return: none
    """
    logger.info("EC2:%r: Creating bucket %r...", ec2.api.region, bucket_name)
    ec2.create_s3_bucket(bucket_name)  # Will return false if the bucket exists

    if ec2.object_exists_in_bucket(bucket_name=bucket_name, object_key=ami_name):
        logger.info('EC2:%r: Image %r in bucket %r already', ec2.api.region, ami_name, bucket_name)
        return

    logger.info('EC2:%r: uploading file %r to bucket %r...', ec2.api.region, file_path, bucket_name)
    ec2.upload_file_to_s3_bucket(bucket_name, file_path=file_path, file_name=ami_name)
    logger.info('EC2:%r: File uploading done ...', ec2.api.region.name)


def cleanup_s3(ec2, bucket_name, ami_name):
    """Cleanup the bucket we used for upload
    :param ec2: mgmtsystem:EC2System object
    :param bucket_name: string name of bucket to create/upload to
    :param ami_name: string name of the file in the bucket
    """
    logger.info('EC2:%r: Removing object "%r" from bucket "%r"',
                ec2.api.region.name, ami_name, bucket_name)
    ec2.delete_objects_from_s3_bucket(bucket_name=bucket_name, object_keys=[ami_name])


def run(template_name, image_url, stream, **kwargs):
    """
    Download file from image_url, upload it to an S3 bucket and import into ec2

    Should handle all ec2 regions and minimize uploading by copying images
    :param template_name: string name of the template
    :param image_url: string url to download template image
    :param stream: string stream name
    :param kwargs: other kwargs
    :return: none
    """
    mgmt_sys = cfme_data['management_systems']
    ami_name = template_name
    prov_to_upload = []
    valid_providers = [
        prov_key
        for prov_key in mgmt_sys
        if (mgmt_sys[prov_key]['type'] == 'ec2') and ('disabled' not in mgmt_sys[prov_key]['tags'])
    ]

    if valid_providers:
        logger.info("Uploading to following enabled ec2 providers/regions: %r", valid_providers)
    else:
        logger.info('ERROR: No providers found with ec2 type and no disabled tag')
        return

    # Look for template name on all ec2 regions, in case we can just copy it
    # Also ec2 lets you upload duplicate names, so we'll skip upload if its already there
    for prov_key in valid_providers:
        ec2 = get_mgmt(provider_key=prov_key)
        try:
            ami_id = check_for_ami(ec2, ami_name)
        except MultipleImagesError:
            logger.info('ERROR: Already multiple images with name "%r"', ami_name)
            return

        if ami_id:
            # TODO roll this into a flag that copies it to regions without it
            logger.info('EC2 %r: AMI already exists with name "%r"', prov_key, ami_name)
            continue
        else:
            # Need to upload on this region
            prov_to_upload.append(prov_key)

    # See if we actually need to upload
    if not prov_to_upload:
        logger.info('DONE: No templates to upload, all regions have the ami: "%r"', ami_name)
        return

    # download image
    logger.info("INFO: Starting image download %r ...", kwargs.get('image_url'))
    file_name, file_path = download_image_file(image_url)
    logger.info("INFO: Image downloaded %r ...", file_path)

    # TODO: thread + copy within amazon for when we have multiple regions enabled
    # create ami's in the regions
    for prov_key in prov_to_upload:
        region = mgmt_sys[prov_key].get('region', prov_key)
        bucket_name = mgmt_sys[prov_key].get('upload_bucket_name', 'cfme-template-upload')

        logger.info('EC2:%r:%r Starting S3 upload of %r', prov_key, region, file_path)
        ec2 = get_mgmt(provider_key=prov_key)
        upload_to_s3(ec2=ec2, bucket_name=bucket_name, ami_name=ami_name, file_path=file_path)

        create_image(ec2=ec2, ami_name=ami_name, bucket_name=bucket_name)

        cleanup_s3(ec2=ec2, bucket_name=bucket_name, ami_name=ami_name)

        # Track it
        logger.info("EC2:%r:%r Adding template %r to trackerbot for stream",
                    prov_key, region, ami_name, stream)
        trackerbot.trackerbot_add_provider_template(stream, prov_key, ami_name)
        logger.info('EC2:%r:%r Template %r creation complete', prov_key, region, ami_name)


if __name__ == '__main__':
    args = parse_cmd_line()
    kwargs = cfme_data['template_upload']['template_upload_ec2']
    final_kwargs = make_kwargs(args, **kwargs)

    run(**final_kwargs)
