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
import os
import urllib2
from threading import Lock, Thread

from mgmtsystem import GoogleCloudSystem
from utils.conf import cfme_data
from utils.conf import credentials
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


def download_image_file(image_url, destination=None):
    file_name = image_url.split('/')[-1]
    u = urllib2.urlopen(image_url)
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    file_path = os.path.abspath(file_name)
    if os.path.isfile(file_name):
        if file_size == os.path.getsize(file_name):
            return (file_name, file_path)
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
        status = r"{:.2f}".format(file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8) * (len(status) + 1)
        print('r')
        print(status)

    f.close()
    return (file_name, file_path)


def check_template_name(name):
    pattern = re.compile("(?:[a-z](?:[-a-z0-9]{0,61}[a-z0-9])?)")
    match = pattern.match(name)
    if isinstance(match.group(), str) and match.group() != name:
        name = cfme_data['basic_info']['appliance_template']
    return name


def upload_template(project, zone, service_account, image_url,
        template_name, bucket_name, provider):
    try:
        if not bucket_name:
            bucket_name = cfme_data['template_upload']['template_upload_gce']['bucket_name']
        print("GCE:{} Starting image downloading {} ...".format(provider, image_url))
        file_name, file_path = download_image_file(image_url)
        print("GCE:{} Image downloaded {} ...".format(provider, file_path))

        print("GCE:{} Creating bucket and uploading file {}...".format(provider, bucket_name))
        gcloud = GoogleCloudSystem(project=project, zone=zone, service_account=service_account)
        gcloud.create_bucket(bucket_name)
        blob_name = gcloud.get_file_from_bucket(bucket_name, file_name)
        if not blob_name:
            gcloud.upload_file_to_bucket(bucket_name, file_path)
            blob_name = gcloud.get_file_from_bucket(bucket_name, file_name)
        print("GCE:{} File uploading done ...".format(provider))

        print("GCE:{} Creating template/image {}...".format(provider, template_name))
        template_name = check_template_name(template_name)
        gcloud.create_image(image_name=template_name, bucket_url=blob_name.get('selfLink'))
        print("GCE:{} Successfully uploaded the template.".format(provider))
    except Exception as e:
        print(e)
        print("GCE:{} Error occurred in upload_template".format(provider))
        return False
    finally:
        print("GCE:{} End template {} upload...".format(provider, template_name))


def run(**kwargs):
    thread_queue = []
    for provider in list_provider_keys("gce"):
        mgmt_sys = cfme_data['management_systems'][provider]
        gce_credentials = credentials[mgmt_sys['credentials']]

        service_account = gce_credentials['service_account']
        project = mgmt_sys['project']
        zone = mgmt_sys['zone']
        thread = Thread(target=upload_template,
                        args=(project, zone, service_account, kwargs.get('image_url'),
                            kwargs.get('template_name'), kwargs.get('bucket_name'), provider))
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
