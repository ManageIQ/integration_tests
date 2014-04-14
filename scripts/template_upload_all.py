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


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--dir_url', dest='dir_url',
                        help='URL of a web directory containing links to CFME images',
                        default=None)
    args = parser.parse_args()
    return args

#TODO allow suffix
def template_name(image_name):
    #MIQ
    pattern = re.compile('[^\d]*?TEST-BUILD-[^\d]*(\d*).\w*')
    result = pattern.findall(image_name)
    if result:
        #for now, actual version for MIQ is manually defined.
        actual_version = '30'
        return "miq-" + actual_version + "-" + result[0][4:8]
    else:
        #CFME
        pattern = re.compile('[^\d]*(\d*).\w*?')
        result = pattern.findall(image_name)
        #this will produce: 'cfme-30-0304'
        return "cfme-" + result[0] + result[1] + "-" + result[3] + result[4]


def make_kwargs_rhevm(cfme_data, provider):
    data = cfme_data['management_systems'][provider]
    temp_up = cfme_data['template_upload']['template_upload_rhevm']

    edomain = data['template_upload'].get('edomain', None)
    sdomain = data['template_upload'].get('sdomain', None)
    cluster = data['template_upload'].get('cluster', None)
    disk_size = temp_up.get('disk_size', None)
    disk_format = temp_up.get('disk_format', None)
    disk_interface = temp_up.get('disk_interface', None)

    kwargs = {}
    kwargs.update({'provider':provider})
    if edomain:
        kwargs.update({'edomain':edomain})
    if sdomain:
        kwargs.update({'sdomain':sdomain})
    if cluster:
        kwargs.update({'cluster':cluster})
    if disk_size:
        kwargs.update({'disk_size':disk_size})
    if disk_format:
        kwargs.update({'disk_format':disk_format})
    if disk_interface:
        kwargs.update({'disk_interface':disk_interface})

    return kwargs


def make_kwargs_rhos(cfme_data, provider):
    data = cfme_data['management_systems'][provider]

    tenant_id = data['template_upload'].get('tenant_id', None)

    kwargs = {}
    kwargs.update({'provider':provider})
    if tenant_id:
        kwargs.update({'tenant_id':tenant_id})

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

    kwargs = {}
    kwargs.update({'provider':provider})
    if datastore:
        kwargs.update({'datastore':datastore})
    if cluster:
        kwargs.update({'cluster':cluster})
    if datacenter:
        kwargs.update({'datacenter':datacenter})
    if host:
        kwargs.update({'host':host})
    if template:
        kwargs.update({'template':template})
    if upload:
        kwargs.update({'upload':upload})
    if disk:
        kwargs.update({'disk':disk})

    return kwargs


def browse_directory(dir_url):
    name_dict = {}
    with closing(urlopen(dir_url)) as urlpath:
        string_from_url = urlpath.read()

    rhevm_pattern = re.compile('<a href="?\'?([^"\']*rhevm[^"\'>]*)')
    rhevm_image_name = rhevm_pattern.findall(string_from_url)
    rhos_pattern = re.compile('<a href="?\'?([^"\']*rhos[^"\'>]*)')
    rhos_image_name = rhos_pattern.findall(string_from_url)
    vsphere_pattern = re.compile('<a href="?\'?([^"\']*vsphere[^"\'>]*)')
    vsphere_image_name = vsphere_pattern.findall(string_from_url)

    if len(rhevm_image_name) is not 0:
        name_dict.update({'template_upload_rhevm': rhevm_image_name[0]})
    if len(rhos_image_name) is not 0:
        name_dict.update({'template_upload_rhos': rhos_image_name[0]})
    if len(vsphere_image_name) is not 0:
        name_dict.update({'template_upload_vsphere': vsphere_image_name[0]})

    if not dir_url.endswith('/'):
        dir_url = dir_url + '/'

    for key, val in name_dict.iteritems():
        name_dict[key] = dir_url + val

    return name_dict


if __name__ == "__main__":

    args = parse_cmd_line()

    dir_url = args.dir_url or cfme_data['basic_info']['cfme_images_url']

    dir_files = browse_directory(dir_url)

    mgmt_sys = cfme_data['management_systems']

    kwargs = {}

    for provider in mgmt_sys:
        if mgmt_sys[provider].get('template_upload', None):
            if 'rhevm' in provider:
                module = 'template_upload_rhevm'
                if module not in dir_files.iterkeys():
                    continue
                kwargs = make_kwargs_rhevm(cfme_data, provider)
            if 'rhos' in provider:
                module = 'template_upload_rhos'
                if module not in dir_files.iterkeys():
                    continue
                kwargs = make_kwargs_rhos(cfme_data, provider)
            if 'vsphere' in provider:
                module = 'template_upload_vsphere'
                if module not in dir_files.iterkeys():
                    continue
                kwargs = make_kwargs_vsphere(cfme_data, provider)

            if kwargs:
                kwargs.update({'image_url':dir_files[module]})

                if cfme_data['template_upload']['name'] == 'auto':
                    kwargs.update({'template_name':template_name(dir_files[module])})

                print "---Start of %s: %s---" % (module, provider)

                try:
                    getattr(__import__(module), "run")(**kwargs)
                except:
                    print "Exception: Module '%s' with provider '%s' exitted with error." % (module, provider)

                print "---End of %s: %s---" % (module, provider)
