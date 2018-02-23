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

CFME_ID = "cfme"
MIQ_ID = "manageiq"

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


def template_name(image_link, timestamp, version=None):
    """Generate a template name from given link, a timestamp, and optional version string
    This method should handle naming templates from the following URL types:
        - http://<build-server-address>/builds/manageiq/master/latest/
        - http://<build-server-address>/builds/manageiq/gaprindashvili/stable/
        - http://<build-server-address>/builds/manageiq/fine/stable/
        - http://<build-server-address>/builds/cfme/5.7/stable/
        - http://<build-server-address>/builds/cfme/5.9/latest/

    These builds fall into a few categories:
        - MIQ nightly (master/latest)  (upstream)
        - MIQ stable (<name>/stable)  (upstream_stable, upstream_fine, etc)
        - CFME nightly (<stream>/latest)  (downstream-nightly)
        - CFME stream (<stream>/stable)  (downstream-<stream>)

    The generated template names should follow the syntax with 5 digit version numbers:
        - MIQ nightly: miq-nightly-<yyyymmdd>  (miq-nightly-201711212330)
        - MIQ stable: miq-stable-<name>-<number>-yyyymmdd  (miq-stable-fine-4-20171024)
        - CFME nightly: cfme-nightly-<version>-<yyyymmdd>  (cfme-nightly-59000-20170901)
        - CFME stream: cfme-<version>-<yyyymmdd>  (cfme-57402-20171202)

    Release names for upstream will be truncated to 5 letters (thanks gaprindashvili...)
    """

    pattern = re.compile(r'.*/(.*)')
    image_name = pattern.findall(image_link)[0].lower()
    formatted_timestamp = '{year}{month}{day}'.format(year=str(timestamp.year),
                                                      month=str(timestamp.month).zfill(2),
                                                      day=str(timestamp.day).zfill(2))
    # CFME
    if CFME_ID in image_name:
        if 'nightly' in image_name:
            # CFME nightly
            name = '-'.join([CFME_ID,
                             'nightly',
                             version,
                             formatted_timestamp])
        else:
            # CFME stream
            name = '-'.join([CFME_ID,
                             version,
                             formatted_timestamp])
        return name

    # MIQ
    elif MIQ_ID in image_name:
        if "master/latest" in image_link:
            # MIQ nightly
            name = '-'.join(['miq',
                             'nightly',
                             formatted_timestamp])
        else:
            # MIQ stable
            # Handle named MIQ releases, dropping provider and capturing release and date
            # regex includes -\d on the end to stop the lazy capture past the release name+number
            pattern = re.compile(r'manageiq-(?:[\w]+?)-(?P<release>[\w]+?)-(?P<number>\d)-\d{3,}')
            # Use match so we can use regex group names
            result = pattern.match(image_name)
            short_release = result.group('release')[:5]
            number = result.group('number')
            name = '-'.join(['miq',
                             'stable',
                             short_release,
                             number,
                             formatted_timestamp])

        return name

    # Podified
    elif 'openshift' in image_link:
        return '-'.join([CFME_ID,
                         version,
                         formatted_timestamp])


def get_version_and_timestamp(dir_url):
    """Return a tuple of version string and datetime object

    Version string is padded to 5 digit"""
    version_url = '/'.join([dir_url, 'version'])

    try:
        urlo = urlopen(version_url)
    except Exception:
        logger.warning('No version file, must be upstream builds')
        urlo = None

    if urlo:
        # version string from file
        version = urlo.read()
        match = re.search(
            '^(?P<major>\d{1})\.?(?P<minor>\d{1})\.?(?P<patch>\d{1})\.?(?P<build>\d{1,2})',
            str(version)
        )
        version_str = ''.join([match.group('major'),
                               match.group('minor'),
                               match.group('patch'),
                               match.group('build').zfill(2)])  # zero left-pad to given length
    else:
        # no version string file
        version_str = None

        # setup alternate file for timestamp query
        keyfile_url = '/'.join([dir_url, 'manageiq_public.key'])
        try:
            urlo = urlopen(keyfile_url)
        except Exception:
            logger.warning('No manageiq_public.key file, trying for SHA256SUM file')
            urlo = urlopen('/'.join([dir_url, 'SHA256SUM']))

    logger.info('Parsed version number (empty for upstream): %s', version_str)

    # build datetime from URL header
    headers = urlo.info()
    datetime_format = "%a, %d %b %Y %H:%M:%S %Z"
    timestamp = datetime.datetime.strptime(headers.getheader("Last-Modified"),
                                           datetime_format)
    return version_str, timestamp


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
            version, timestamp = get_version_and_timestamp(url)
            kwargs['template_name'] = template_name(
                dir_files[module],
                timestamp,
                version)
            logger.info('template_name: %s', kwargs['template_name'])
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
        return 0
    else:
        logger.warning('No URL match, not calling any upload modules.')
        return 1


if __name__ == "__main__":

    args = parse_cmd_line()
    sys.exit(main())
