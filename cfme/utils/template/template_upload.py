#!/usr/bin/env python3
import argparse
import sys
from threading import Thread

from miq_version import TemplateName

from cfme.utils.conf import cfme_data
from cfme.utils.log import add_stdout_handler
from cfme.utils.log import logger
from cfme.utils.providers import list_provider_keys
from cfme.utils.template.base import ALL_STREAMS
from cfme.utils.template.base import PROVIDER_TYPES
from cfme.utils.template.base import TemplateUploadException
from cfme.utils.template.ec2 import EC2TemplateUpload
from cfme.utils.template.gce import GoogleCloudTemplateUpload
from cfme.utils.template.openstack import OpenstackTemplateUpload
from cfme.utils.template.rhevm import RHEVMTemplateUpload
from cfme.utils.template.rhopenshift import OpenshiftTemplateUpload
from cfme.utils.template.scvmm import SCVMMTemplateUpload
from cfme.utils.template.virtualcenter import VMWareTemplateUpload

CLASS_MAP = {
    'openstack': OpenstackTemplateUpload,
    'virtualcenter': VMWareTemplateUpload,
    'scvmm': SCVMMTemplateUpload,
    'gce': GoogleCloudTemplateUpload,
    'ec2': EC2TemplateUpload,
    'openshift': OpenshiftTemplateUpload,
    'rhevm': RHEVMTemplateUpload
}

add_stdout_handler(logger)


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)

    provider_group = parser.add_mutually_exclusive_group(required=True)
    provider_group.add_argument(
        '--provider-type',
        dest='provider_type',
        choices=PROVIDER_TYPES,
        help='Provider type'
    )
    provider_group.add_argument(
        '--provider',
        nargs='+',
        dest='provider',
        help='Specific provider keys list'
    )
    parser.add_argument(
        '--glance',
        dest='glance_key',
        default=None,
        help='key for the glance server information in cfme_data.template_upload'
    )
    parser.add_argument(
        '--stream',
        dest='stream',
        help='Stream (downstream-59z)name for the image_url, or default to stable/latest in stream'
             'Please check the cfme_data file for current streams.'
    )
    parser.add_argument(
        '--image-url',
        dest='image_url',
        help='URL for the image file to be uploaded. Please use with --stream.'
    )
    parser.add_argument(
        '--template-name',
        dest='template_name',
        help='Set the name of the template'
    )
    parser.add_argument(
        '--print-name-only',
        dest='print_name_only',
        action="store_true",
        help='Only print the template name that will be generated without actually running it.'
    )

    return parser.parse_known_args()


def get_stream_from_image_url(image_url, quiet=False):
    """Get default image URL for a given stream name"""
    # strip trailing / from URL, and strip build number or link (5.11.0.1, latest, stable)
    # to get just https://url/builds/[cfme/manageiq]/[build-stream]
    image_base = '/'.join(image_url.strip('/').split('/')[:-1])
    if not quiet:  # don't log (goes to stdout) when just printing name, for Jenkins
        logger.info('Matching stream name based on image_url base: %s', image_base)
    # look for image_base URL component in basic_info dict
    matching_streams = [key for key, value in ALL_STREAMS.items() if image_base in value]
    if matching_streams:
        # sometimes multiple match, use first
        if len(matching_streams) > 1:
            logger.warning('warning: Multiple stream name matches: %s for URL %s, using first',
                           matching_streams, image_url)
        return matching_streams[0]
    else:
        logger.error('Cannot find stream in image url: %s', image_url)
        raise TemplateUploadException("Cannot find stream from image URL.")


if __name__ == '__main__':
    cmd_line_args = parse_cmd_line()
    cmd_args = cmd_line_args[0]
    specific_args = cmd_line_args[1]

    if cmd_args.image_url and not cmd_args.stream:
        # parse stream from image_url
        image_url = cmd_args.image_url
        stream = get_stream_from_image_url(image_url, quiet=cmd_args.print_name_only)
    elif cmd_args.stream and not cmd_args.image_url:
        # default to base URL for given stream:
        stream = cmd_args.stream
        image_url = ALL_STREAMS[stream]
    else:
        logger.warning("Require either --image-url or --stream")
        sys.exit(1)

    provider_type = cmd_args.provider_type

    template_name = (f"{cmd_args.template_name}-{stream}" if cmd_args.template_name else
                     TemplateName(image_url).template_name)

    if cmd_args.print_name_only:
        print(template_name)
        sys.exit(0)

    if not provider_type or cmd_args.provider:
        provider_types = PROVIDER_TYPES
    elif provider_type in PROVIDER_TYPES:
        provider_types = [provider_type, ]
    else:
        logger.error('Template upload for %r is not implemented yet.', provider_type)
        sys.exit(1)

    thread_queue = []

    # create uploader objects for each provider
    for provider_type in provider_types:
        provider_keys = list_provider_keys(provider_type)
        if cmd_args.provider:
            provider_keys = [x for x in cmd_args.provider if x in provider_keys]

        for provider_key in provider_keys:
            if provider_key not in list_provider_keys(provider_type):
                continue

            # pulling class by provider type
            provider_template_upload = (cfme_data.management_systems[provider_key]
                                        .get('template_upload', {}))
            uploader = CLASS_MAP[provider_type](
                provider_key=provider_key,
                stream=stream,
                template_name=template_name,
                image_url=image_url,
                cmd_line_args=specific_args,
                glance_key=cmd_args.glance_key or provider_template_upload.get('glance_key'))

            if uploader.template_upload_data.get('block_upload', True):
                logger.info("%s:%s Skipped due to block upload.", uploader.log_name, provider_key)
                continue

            if uploader.template_upload_data.get('block_upstream', False) and 'upstream' in stream:
                logger.info("%s:%s Skipped due to block_upstream.", uploader.log_name, provider_key)
                continue

            if (uploader.template_upload_data.get('block_downstream', False) and
                    'downstream' in stream):
                logger.info("%s:%s Skipped due to block_upstream.", uploader.log_name, provider_key)
                continue

            thread = Thread(target=uploader.main)
            thread.daemon = True
            thread_queue.append(thread)
            thread.start()

    if not thread_queue:
        logger.error('No providers or types matched, check arguments')
        sys.exit(1)

    for thread in thread_queue:
        thread.join()
