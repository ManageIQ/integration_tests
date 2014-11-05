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
import datetime

from contextlib import closing
from urllib2 import urlopen, HTTPError

from utils.conf import cfme_data


CFME_BREW_ID = "cfme"
NIGHTLY_MIQ_ID = "manageiq"


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


def template_name(image_link, image_ts, version=None):
    pattern = re.compile(r'.*/(.*)')
    image_name = pattern.findall(image_link)[0]
    image_name = image_name.lower()
    image_dt = get_last_modified(image_link)
    # CFME brew builds
    if CFME_BREW_ID in image_name:
        if version:
            if len(version) == 4:
                version = version[:-1] + '0' + version[-1:]
            return "cfme-%s-%s%s%s" % (version, image_ts, image_dt.hour, image_dt.minute)
        else:
            pattern = re.compile(r'[^\d]*?-(\d).(\d)-(\d).*')
            result = pattern.findall(image_name)
            # cfme-pppp-x.y-z.arch.[pppp].ova => cfme-nightly-x.y-z
            return "cfme-nightly-%s.%s-%s" % (result[0][0], result[0][1], result[0][2])
    # nightly builds MIQ
    elif NIGHTLY_MIQ_ID in image_name:
        pattern = re.compile(r'[^\d]*?-master-(\d*)-*')
        result = pattern.findall(image_name)
        if version:
            # manageiq-pppp-bbbbbb-yyyymmddhhmm.ova => miq-nightly-vvvv-yyyymmddhhmm
            return "miq-nightly-%s-%s" % (version, result[0])
        else:
            # manageiq-pppp-bbbbbb-yyyymmddhhmm.ova => miq-nightly-yyyymmddhhmm
            return "miq-nightly-%s" % result[0]
    # z-stream
    else:
        pattern = re.compile(r'[.-](\d+(?:\d+)?)')
        result = pattern.findall(image_name)
        if version:
            # CloudForms-x.y-yyyy-mm-dd.i-xxx*.ova => cfme-vvvv-mmdd
            # If build number < 10, pad it with a 0.
            if len(version) == 4:
                version = version[:-1] + '0' + version[-1:]
            return "cfme-%s-%s%s%s%s" % (version, result[3], result[4],
                                         image_dt.hour, image_dt.minute)
        else:
            # CloudForms-x.y-yyyy-mm-dd.i-xxx*.ova => cfme-xy-yyyymmddi
            str_res = ''.join(result)
            return "cfme-%s-%s" % (str_res[0:2], str_res[2:])


def get_version(dir_url):
    if not dir_url.endswith("/"):
        dir_url += "/"

    version_url = dir_url + "version"

    try:
        urlo = urlopen(version_url)
    except Exception:
        return None

    version = urlo.read()

    return version.rstrip().replace('.', '')


def get_last_modified(image_url):
    """Returns a datetime object for when the image was last modified."""
    format = "%a, %d %b %Y %H:%M:%S %Z"
    try:
        urlo = urlopen(image_url)
    except Exception:
        return None

    headers = urlo.info()
    return datetime.datetime.strptime(headers.getheader("Last-Modified"), format)


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
    try:
        with closing(urlopen(dir_url)) as urlpath:
            string_from_url = urlpath.read()
    except HTTPError as e:
        print str(e)
        print "Skipping: %s" % dir_url
        return None

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

    for key in name_dict.keys():
        date = urlopen(name_dict[key]).info().getdate('last-modified')
        name_dict[key + "_date"] = "%02d" % date[1] + "%02d" % date[2]

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
        if not dir_files:
            continue
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
                        kwargs['template_name'] = template_name(
                            dir_files[module],
                            dir_files[module + "_date"],
                            get_version(url))

                    print "---Start of %s: %s---" % (module, provider)

                    try:
                        getattr(__import__(module), "run")(**kwargs)
                    except Exception as woops:
                        print "Exception: Module '%s' with provider '%s' exitted with error." \
                            % (module, provider)
                        print woops

                    print "---End of %s: %s---" % (module, provider)
