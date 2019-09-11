#!/usr/bin/env python3
"""
Script to upload iso/qcow2 images to Glance server

Usage:
1.scripts/image_upload_glance.py --image cfme-rhevm-5.8.2.1-1.x86_64.qcow2 \
                                 --image_name_in_glance cfme-5821.qcow2 \
                                 --provider glance11 \
                                 --disk_format qcow2
2.scripts/image_upload_glance.py --image cfme-rhevm-5.8.2.1-1.x86_64.qcow2 \
                                 --image_name_in_glance cfme-rhevm-5.8.2.1-1.x86_64.qcow2 \
                                 --provider glance11 \
3.scripts/image_upload_glance.py --image_name_in_glance cfme-5922.qcow2 \
                                 --provider glance11-server \
                                 --url http://user:pswd@xyz:8080/cfme-rhevm-5.9.0.22-1.x86_64.qcow2

Note : If disk_format is not passed, it defaults to qcow2.
"""
import argparse
import sys

from glanceclient import Client
from keystoneauth1 import loading
from keystoneauth1 import session

from cfme.utils.conf import credentials
from cfme.utils.config_data import cfme_data


def parse_cmd_line():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    # Either --url or --image should be present, but not both.
    parser.add_argument('--image_name_in_glance', help='Image name in Glance', required=True)
    parser.add_argument('--provider', help='Glance provider key in cfme_data', required=True)
    parser.add_argument('--disk_format', help='Disk format of image', default='qcow2')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--image', help='Image to be uploaded to Glance')
    group.add_argument('--url', help='Add a backend location url to an image')

    args = parser.parse_args()
    return args


def upload_to_glance(image, image_name_in_glance, provider, disk_format, url):
    """
    Upload iso/qcow2/ova images to Glance.
    """
    api_version = '2'  # python-glanceclient API version
    provider_dict = cfme_data['template_upload'][provider]
    creds_key = provider_dict['credentials']

    loader = loading.get_plugin_loader('password')
    auth = loader.load_from_options(
        auth_url=provider_dict['auth_url'],
        username=credentials[creds_key]['username'],
        password=credentials[creds_key]['password'],
        tenant_name=credentials[creds_key]['tenant'])
    glance_session = session.Session(auth=auth)
    glance = Client(api_version, session=glance_session)

    # Two images on Glance could have the same name since Glance assigns them different IDS.
    # So, we are running a check to make sure an image with the same name doesn't already exist.
    for img in glance.images.list():
        if img.name == image_name_in_glance:
            print("image_upload_glance: Image already exists on Glance server")
            return

    glance_img = glance.images.create(name=image_name_in_glance)
    # Update image properties before uploading the image.
    glance.images.update(glance_img.id, container_format="bare")
    glance.images.update(glance_img.id, disk_format=disk_format)
    glance.images.update(glance_img.id, visibility="public")
    if image:
        glance.images.upload(glance_img.id, open(image, 'rb'))
    elif url:
        glance.images.add_location(glance_img.id, url, {})


def run(**kwargs):
    upload_to_glance(kwargs['image'], kwargs['image_name_in_glance'], kwargs['provider'],
        kwargs['disk_format'], kwargs['url'])


if __name__ == "__main__":
    args = parse_cmd_line()
    kwargs = dict(args._get_kwargs())
    sys.exit(run(**kwargs))
