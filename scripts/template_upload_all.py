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
    - template_upload_scvmm.py
    - template_upload_vsphere.py
"""

import argparse
import re
import datetime
import sys
import cfme.utils
from urlparse import urljoin
from contextlib import closing
from urllib2 import urlopen, HTTPError

from cfme.utils import path, trackerbot
from cfme.utils.conf import cfme_data
from cfme.utils.log import logger, add_stdout_handler

CFME_BREW_ID = "cfme"
NIGHTLY_MIQ_ID = "manageiq"

add_stdout_handler(logger)


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--stream', dest='stream',
                        help='cfme Stream template to deploy(downstream, upstream, upstream_stable)'
                             'please check the cfme_data file for current streams. old streams'
                             'can be specified as e.g downstream_542, downstream_532,'
                             'upstream',
                        default=None)
    parser.add_argument('--image_url', dest='image_url',
                        help='url for the image to be uploaded',
                        default=None)
    parser.add_argument('--provider-type', dest='provider_type',
                        help='Type of provider to upload to (virtualcenter, rhevm,'
                             'openstack, gce, scvmm)',
                        default=None)
    parser.add_argument('--provider-version', dest='provider_version',
                        help='Version of chosen provider',
                        default=None)
    parser.add_argument('--provider-data', dest='provider_data',
                        help='local yaml file path, to use local provider_data & not conf/cfme_data'
                             'to be useful for template upload/deploy by non cfmeqe',
                        default=None)
    args = parser.parse_args()
    return args


def template_name(image_link, image_ts, checksum_link, version=None):
    pattern = re.compile(r'.*/(.*)')
    image_name = pattern.findall(image_link)[0]
    image_name = image_name.lower()
    image_dt = get_last_modified(checksum_link)
    # CFME brew builds
    if CFME_BREW_ID in image_name:
        if 'nightly' in image_name:
            # 5.6+ nightly
            # cfme-rhevm-5.6.0.0-nightly-20160308112121-1.x86_64.rhevm.ova
            # => cfme-nightly-5600-201603081121 (YYYYMMDDHHmm)
            pattern = re.compile(r'.*-nightly-(\d+).*')
            result = pattern.findall(image_name)
            return "cfme-nightly-{}-{}".format(version, result[0][:-2])
        elif version:
            # proper build
            if len(version) == 4:
                version = version[:-1] + '0' + version[-1:]
            return "cfme-{}-{}{}{}".format(version, image_ts, image_dt.hour, image_dt.minute)
        else:
            # other nightly; leaving it in in case this template-naming comes back
            pattern = re.compile(r'[^\d]*?-(\d).(\d)-(\d).*')
            result = pattern.findall(image_name)
            # cfme-pppp-x.y-z.arch.[pppp].ova => cfme-nightly-x.y-z
            return "cfme-nightly-{}.{}-{}".format(result[0][0], result[0][1], result[0][2])
    # nightly builds MIQ
    elif NIGHTLY_MIQ_ID in image_name:
        if "master" in image_name:
            pattern = re.compile(r'[^\d]*?-master-(\d*)-*')
        else:
            pattern = re.compile(r'[^\d]*?-(\w*)-(\d*)-(\d*)-*')
        result = pattern.findall(image_name)
        if version:
            # manageiq-pppp-bbbbbb-yyyymmddhhmm.ova => miq-nightly-vvvv-yyyymmddhhmm
            return "miq-nightly-{}-{}".format(version, result[0])
        elif "stable" in image_link:
            # Handle named MIQ releases, dropping provider and capturing release and date
            if 'master' not in image_link:
                pattern = re.compile(r'manageiq-([^\d]|ec2)*?-(?P<release>[-.\w]*?)'
                                     r'-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})')
                # Use match so we can use regex group names
                result = pattern.match(image_name)
                return "miq-stable-{}-{}{}{}".format(result.group('release'),
                                                     result.group('year'),
                                                     result.group('month'),
                                                     result.group('day'))
            return "miq-stable-{}-{}".format(result[0][0], result[0][2])
        else:
            # manageiq-pppp-bbbbbb-yyyymmddhhmm.ova => miq-nightly-yyyymmddhhmm
            return "miq-nightly-{}".format(result[0])

    elif 'openshift' in image_link:
        return 'cfme-{}-{}{}'.format(version, image_dt.strftime('%m'), image_dt.strftime('%d'))
    # z-stream
    else:
        pattern = re.compile(r'[.-](\d+(?:\d+)?)')
        result = pattern.findall(image_name)
        if version:
            # CloudForms-x.y-yyyy-mm-dd.i-xxx*.ova => cfme-vvvv-mmdd
            # If build number < 10, pad it with a 0.
            if len(version) == 4:
                version = version[:-1] + '0' + version[-1:]
            return "cfme-{}-{}{}{}{}".format(version, result[3], result[4],
                                         image_dt.hour, image_dt.minute)
        else:
            # CloudForms-x.y-yyyy-mm-dd.i-xxx*.ova => cfme-xy-yyyymmddi
            str_res = ''.join(result)
            return "cfme-{}-{}".format(str_res[0:2], str_res[2:])


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

    edomain = data['template_upload'].get('edomain')
    sdomain = data['template_upload'].get('sdomain')
    cluster = data['template_upload'].get('cluster')
    disk_size = temp_up.get('disk_size')
    disk_format = temp_up.get('disk_format')
    disk_interface = temp_up.get('disk_interface')

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

    tenant_id = data['template_upload'].get('tenant_id')

    kwargs = {'provider': provider}
    if tenant_id:
        kwargs['tenant_id'] = tenant_id

    return kwargs


def make_kwargs_scvmm(cfme_data, provider):
    data = cfme_data['management_systems'][provider]

    tenant_id = data['template_upload'].get('tenant_id')

    kwargs = {'provider': provider}
    if tenant_id:
        kwargs['tenant_id'] = tenant_id

    return kwargs


def make_kwargs_vsphere(cfme_data, provider):
    data = cfme_data['management_systems'][provider]
    temp_up = cfme_data['template_upload']['template_upload_vsphere']

    datastore = data['provisioning'].get('datastore')
    cluster = data['template_upload'].get('cluster')
    datacenter = data['template_upload'].get('datacenter')
    host = data['template_upload'].get('host')
    template = temp_up.get('template')
    upload = temp_up.get('upload')
    disk = temp_up.get('disk')
    proxy = data['template_upload'].get('proxy')

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
    except HTTPError:
        logger.exception("Skipping: %r", dir_url)
        return None

    rhevm_pattern = re.compile(r'<a href="?\'?([^"\']*(?:rhevm\.ova|ovirt)[^"\'>]*)')
    rhevm_image_name = rhevm_pattern.findall(string_from_url)
    rhos_pattern = re.compile(r'<a href="?\'?([^"\']*(?:rhos|openstack|rhelosp)[^"\'>]*)')
    rhos_image_name = rhos_pattern.findall(string_from_url)
    scvmm_pattern = re.compile(r'<a href="?\'?([^"\']*hyperv[^"\'>]*)')
    scvmm_image_name = scvmm_pattern.findall(string_from_url)
    vsphere_pattern = re.compile(r'<a href="?\'?([^"\']*vsphere[^"\'>]*)')
    vsphere_image_name = vsphere_pattern.findall(string_from_url)
    google_pattern = re.compile(r'<a href="?\'?([^"\']*gce[^"\'>]*)')
    google_image_name = google_pattern.findall(string_from_url)
    ec2_pattern = re.compile(r'<a href="?\'?([^"\']*ec2[^"\'>]*)')
    ec2_image_name = ec2_pattern.findall(string_from_url)
    openshift_pattern = re.compile(r'<a href="?\'?(openshift-pods/*)')
    openshift_image_name = openshift_pattern.findall(string_from_url)

    if len(rhevm_image_name) is not 0:
        name_dict['template_upload_rhevm'] = rhevm_image_name[0]
    if len(rhos_image_name) is not 0:
        name_dict['template_upload_rhos'] = rhos_image_name[0]
    if len(scvmm_image_name) is not 0:
        name_dict['template_upload_scvmm'] = scvmm_image_name[0]
    if len(vsphere_image_name) is not 0:
        name_dict['template_upload_vsphere'] = vsphere_image_name[0]
    if len(google_image_name) is not 0:
        name_dict['template_upload_gce'] = google_image_name[0]
    if len(ec2_image_name) is not 0:
        name_dict['template_upload_ec2'] = ec2_image_name[0]
    if len(openshift_image_name) is not 0:
        name_dict['template_upload_openshift'] = openshift_image_name[0]

    for key, val in name_dict.iteritems():
        name_dict[key] = urljoin(dir_url, val)

    for key in name_dict.keys():
        if key == 'template_upload_openshift':
            # this is necessary because headers don't contain last-modified date for folders
            #  cfme-template is disposed in templates everywhere except 'latest' in 5.9
            # todo: remove this along with refactoring script
            if '5.8' in name_dict[key] or ('5.9' in name_dict[key] and 'latest' in name_dict[key]):
                url = urljoin(name_dict[key], 'cfme-template.yaml')
            else:
                url = urljoin(name_dict[key], 'templates/cfme-template.yaml')
        else:
            url = name_dict[key]
        date = urlopen(url).info().getdate('last-modified')
        name_dict[key + "_date"] = "%02d" % date[1] + "%02d" % date[2]

    return name_dict


def main():

    urls = cfme_data['basic_info']['cfme_images_url']
    stream = args.stream or cfme_data['template_upload']['stream']
    upload_url = args.image_url
    provider_type = args.provider_type or cfme_data['template_upload']['provider_type']

    if args.provider_data is not None:
        local_datafile = open(args.provider_data, 'r').read()
        create_datafile = open(path.conf_path.strpath + '/provider_data.yaml', 'w')
        create_datafile.write(local_datafile)
        create_datafile.close()
        provider_data = cfme.utils.conf.provider_data
        stream = provider_data['stream']

    if stream:
        urls = {}
        image_url = cfme_data['basic_info']['cfme_images_url']
        urls[stream] = image_url.get(stream)
        if not urls[stream]:
            image_url = cfme_data['basic_info']['cfme_old_images_url']
            urls[stream] = image_url.get(stream)
        if not urls[stream]:
            base_url = cfme_data['basic_info']['cfme_old_images_url']['base_url']
            version = ''.join(re.findall(r'(\d+)', stream))
            urls[stream] = \
                base_url + '.'.join(version[:2]) + '/' + '.'.join(version) + '/'

    for key, url in urls.iteritems():
        if stream is not None:
            if key != stream:
                continue
        if upload_url:
            # strip trailing slashes just in case
            if url.rstrip('/') != upload_url.rstrip('/'):
                continue
        dir_files = browse_directory(url)
        if not dir_files:
            continue
        checksum_url = url + "SHA256SUM"
        try:
            urlopen(checksum_url)
        except Exception:
            logger.exception("No valid checksum file for %r, Skipping", key)
            continue

        kwargs = {}
        module = None
        if not provider_type:
            sys.exit('specify the provider_type')

        if provider_type == 'openstack':
            module = 'template_upload_rhos'
            if module not in dir_files.iterkeys():
                continue
        elif provider_type == 'rhevm':
            module = 'template_upload_rhevm'
            if module not in dir_files.iterkeys():
                continue
        elif provider_type == 'virtualcenter':
            module = 'template_upload_vsphere'
            if module not in dir_files.iterkeys():
                continue
        elif provider_type == 'scvmm':
            module = 'template_upload_scvmm'
            if module not in dir_files.iterkeys():
                continue
        elif provider_type == 'gce':
            module = 'template_upload_gce'
            if module not in dir_files.iterkeys():
                continue
        elif provider_type == 'ec2':
            module = 'template_upload_ec2'
            if module not in dir_files.iterkeys():
                continue
        elif provider_type == 'openshift':
            module = 'template_upload_openshift'
            if module not in dir_files.iterkeys():
                continue

        if not module:
            logger.error('Could not match module to given provider type')
            return 1
        kwargs['stream'] = stream
        kwargs['image_url'] = dir_files[module]
        if args.provider_data is not None:
            kwargs['provider_data'] = provider_data
        else:
            kwargs['provider_data'] = None

        if cfme_data['template_upload']['automatic_name_strategy']:
            kwargs['template_name'] = template_name(
                dir_files[module],
                dir_files[module + "_date"],
                checksum_url,
                get_version(url)
            )
            if not stream:
                # Stream is none, using automatic naming strategy, parse stream from template name
                template_parser = trackerbot.parse_template(kwargs['template_name'])
                if template_parser.stream:
                    kwargs['stream'] = template_parser.group_name

        logger.info("TEMPLATE_UPLOAD_ALL:-----Start of %r upload on: %r--------",
            kwargs['template_name'], provider_type)

        logger.info("Executing %r with the following kwargs: %r", module, kwargs)
        getattr(__import__(module), "run")(**kwargs)

        logger.info("TEMPLATE_UPLOAD_ALL:------End of %r upload on: %r--------",
            kwargs['template_name'], provider_type)


if __name__ == "__main__":

    args = parse_cmd_line()
    sys.exit(main())
