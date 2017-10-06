#!/usr/bin/env python2

"""
Script to upload iso/qcow2/ova images to Glance server

Usage:
1.scripts/image_upload_glance.py --image cfme-rhevm-5.8.2.1-1.x86_64.qcow2 \
                                 --image_name_in_glance cfme-5821.qcow2 \
                                 --provider glance11 \
                                 --disk_format qcow2
2.scripts/image_upload_glance.py --image cfme-rhevm-5.8.2.1-1.x86_64.qcow2 \
                                 --image_name_in_glance cfme-rhevm-5.8.2.1-1.x86_64.qcow2 \
                                 --provider glance11 \

If disk_format is not passed, it defaults to qcow2.
"""
import argparse
import sys

from cfme.utils.conf import cfme_data, credentials
from keystoneauth1 import loading
from keystoneauth1 import session
from glanceclient import Client


def upload_to_glance(image, image_name_in_glance, provider, disk_format):
    """
    Upload iso/qcow2/ova images to Glance.
    """
    api_version = '2'  # python-glanceclient API version
    provider_dict = cfme_data['management_systems'][provider]
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
            print("Image already exists on Glance server")
            sys.exit(127)

    glance_img = glance.images.create(name=image_name_in_glance)
    # Update image properties before uploading the image.
    glance.images.update(glance_img.id, container_format="bare")
    glance.images.update(glance_img.id, disk_format=disk_format)
    glance.images.update(glance_img.id, visibility="public")
    glance.images.upload(glance_img.id, open(image, 'rb'))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--image', help='Image to be uploaded to Glance', required=True)
    parser.add_argument('--image_name_in_glance', help='Image name in Glance', required=True)
    parser.add_argument('--provider', help='Glance provider key in cfme_data', required=True)
    parser.add_argument('--disk_format', help='Disk format of image', default='qcow2')

    args = parser.parse_args()

    upload_to_glance(args.image, args.image_name_in_glance, args.provider, args.disk_format)


if __name__ == "__main__":
    sys.exit(main())
