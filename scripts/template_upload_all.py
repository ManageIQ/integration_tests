#!/usr/bin/env python2

"""This script takes an url to a web directory containing links to CFME *.ova images, and runs
whatever uploader script is needed to upload the image & make a template from it. When this ends,
you should have template ready for deploying on respective providers.

This script takes only one parameter, which you can specify either by command-line argument, or
it can be found in cfme_data['basic_info'] section.

The scripts for uploading templates to providers can be also used standalone, with arguments in
cfme_data['template_upload'] and/or provided as a command-line arguments.

The scripts for respective providers are:
    - template_upload_rhevm.py
    - template_upload_rhos.py
    - template_upload_vsphere.py
"""

import argparse
import re

from contextlib import closing
from urllib2 import urlopen

from utils.conf import cfme_data


MIQ_ACTUAL_VERSION = '31'


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--stream', dest='stream',
                        help='Stream to work with (downstream, upstream)',
                        default=None)
    parser.add_argument('--provider-type', dest='provider_type',
                        help='Type of provider to upload to (virtualcenter, rhevm, openstack)',
                        default=None)
    parser.add_argument('--provider-version', dest='provider_version',
                        help='Version of chosen provider',
                        default=None)
    args = parser.parse_args()
    return args


def template_name(image_name):
    #MIQ
    pattern = re.compile(r'[^\d]*?manageiq[^\d]*(\d*).\w*')
    result = pattern.findall(image_name)
    if result:
        #for now, actual version for MIQ is manually defined.
        return "miq-%s-%s" % (MIQ_ACTUAL_VERSION, result[0])
    else:
        #CFME
        pattern = re.compile(r'[.-]\d+(?:-\d+)?')
        result = pattern.findall(image_name)
        return "cfme-%s%s" % (MIQ_ACTUAL_VERSION, ''.join(result))


def make_kwargs_rhevm(cfme_data, provider):
    data = cfme_data['management_systems'][provider]
    temp_up = cfme_data['template_upload']['template_upload_rhevm']

    edomain = data['template_upload'].get('edomain', None)
    sdomain = data['template_upload'].get('sdomain', None)
    cluster = data['template_upload'].get('cluster', None)
    disk_size = temp_up.get('disk_size', None)
    disk_format = temp_up.get('disk_format', None)
    disk_interface = temp_up.get('disk_interface', None)

    kwargs = {'provider': provider}
    if edomain:
        kwargs['edomain'] = edomain
    if sdomain:
        kwargs['sdomain'] = sdomain
    if cluster:
        kwargs['cluster'] = cluster
    if disk_size:
        kwargs['disk_size'] = disk_size
    if disk_format:
        kwargs['disk_format'] = disk_format
    if disk_interface:
        kwargs['disk_interface'] = disk_interface

    return kwargs


def make_kwargs_rhos(cfme_data, provider):
    data = cfme_data['management_systems'][provider]

    tenant_id = data['template_upload'].get('tenant_id', None)

    kwargs = {'provider': provider}
    if tenant_id:
        kwargs['tenant_id'] = tenant_id

    return kwargs


def make_kwargs_vsphere(cfme_data, provider):
    data = cfme_data['management_systems'][provider]
    temp_up = cfme_data['template_upload']['template_upload_vsphere']

    datastore = data['provisioning'].get('datastore', None)
    cluster = data['template_upload'].get('cluster', None)
    datacenter = data['template_upload'].get('datacenter', None)
    host = data['template_upload'].get('host', None)
    template = temp_up.get('template', None)
    upload = temp_up.get('upload', None)
    disk = temp_up.get('disk', None)
    proxy = data['template_upload'].get('proxy', None)

    kwargs = {'provider': provider}
    if datastore:
        kwargs['datastore'] = datastore
    if cluster:
        kwargs['cluster'] = cluster
    if datacenter:
        kwargs['datacenter'] = datacenter
    if host:
        kwargs['host'] = host
    if template:
        kwargs['template'] = template
    if upload:
        kwargs['upload'] = upload
    if disk:
        kwargs['disk'] = disk
    if proxy:
        kwargs['proxy'] = proxy

    return kwargs


def browse_directory(dir_url):
    name_dict = {}
    with closing(urlopen(dir_url)) as urlpath:
        string_from_url = urlpath.read()

    rhevm_pattern = re.compile(r'<a href="?\'?([^"\']*(?:rhevm|ovirt)[^"\'>]*)')
    rhevm_image_name = rhevm_pattern.findall(string_from_url)
    rhos_pattern = re.compile(r'<a href="?\'?([^"\']*(?:rhos|openstack|rhelosp)[^"\'>]*)')
    rhos_image_name = rhos_pattern.findall(string_from_url)
    vsphere_pattern = re.compile(r'<a href="?\'?([^"\']*vsphere[^"\'>]*)')
    vsphere_image_name = vsphere_pattern.findall(string_from_url)

    if len(rhevm_image_name) is not 0:
        name_dict['template_upload_rhevm'] = rhevm_image_name[0]
    if len(rhos_image_name) is not 0:
        name_dict['template_upload_rhos'] = rhos_image_name[0]
    if len(vsphere_image_name) is not 0:
        name_dict['template_upload_vsphere'] = vsphere_image_name[0]

    if not dir_url.endswith('/'):
        dir_url = dir_url + '/'

    for key, val in name_dict.iteritems():
        name_dict[key] = dir_url + val

    return name_dict


if __name__ == "__main__":

    args = parse_cmd_line()

    urls = cfme_data['basic_info']['cfme_images_url']
    stream = args.stream or cfme_data['template_upload']['stream']
    mgmt_sys = cfme_data['management_systems']
    provider_type = args.provider_type or cfme_data['template_upload']['provider_type']
    provider_version = args.provider_version or cfme_data['template_upload']['provider_version']

    for key, url in urls.iteritems():
        if stream is not None:
            if key != stream:
                continue
        dir_files = browse_directory(url)
        kwargs = {}

        for provider in mgmt_sys:
            if provider_type is not None:
                if mgmt_sys[provider]['type'] != provider_type:
                    continue
                if provider_version is not None:
                    if str(mgmt_sys[provider]['version']) != str(provider_version):
                        continue
            if mgmt_sys[provider].get('template_upload', None):
                if 'rhevm' in mgmt_sys[provider]['type']:
                    module = 'template_upload_rhevm'
                    if module not in dir_files.iterkeys():
                        continue
                    kwargs = make_kwargs_rhevm(cfme_data, provider)
                if 'openstack' in mgmt_sys[provider]['type']:
                    module = 'template_upload_rhos'
                    if module not in dir_files.iterkeys():
                        continue
                    kwargs = make_kwargs_rhos(cfme_data, provider)
                if 'virtualcenter' in mgmt_sys[provider]['type']:
                    module = 'template_upload_vsphere'
                    if module not in dir_files.iterkeys():
                        continue
                    kwargs = make_kwargs_vsphere(cfme_data, provider)

                if kwargs:
                    kwargs['image_url'] = dir_files[module]

                    if cfme_data['template_upload']['automatic_name_strategy']:
                        kwargs['template_name'] = template_name(dir_files[module])

                    print "---Start of %s: %s---" % (module, provider)

                    try:
                        getattr(__import__(module), "run")(**kwargs)
                    except:
                        print "Exception: Module '%s' with provider '%s' exitted with error." \
                            % (module, provider)

                    print "---End of %s: %s---" % (module, provider)
