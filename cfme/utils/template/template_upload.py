import argparse
import sys
from threading import Thread

from miq_version import TemplateName

import cfme.utils.conf
from cfme.utils import path
from cfme.utils.conf import cfme_data
from cfme.utils.log import logger, add_stdout_handler
from cfme.utils.providers import list_provider_keys
from cfme.utils.template.base import TemplateUploadException
from cfme.utils.template.ec2 import EC2TemplateUpload
from cfme.utils.template.gce import GoogleCloudTemplateUpload
from cfme.utils.template.openstack import OpenstackTemplateUpload
from cfme.utils.template.scvmm import SCVMMTemplateUpload
from cfme.utils.template.virtualcenter import VMWareTemplateUpload
from cfme.utils.template.openshift import OpenshiftTemplateUpload

add_stdout_handler(logger)
PROVIDER_TYPES = ['openstack', 'virtualcenter', 'scvmm', 'gce', 'ec2', 'openshift']
ALL_STREAMS = cfme_data['basic_info']['cfme_images_url']


class TemplateUpload(object):
    def factory(self, type_, *args, **kwargs):
        if type_ == 'openstack':
            return OpenstackTemplateUpload(*args, **kwargs)

        if type_ == 'virtualcenter':
            return VMWareTemplateUpload(*args, **kwargs)

        if type_ == 'scvmm':
            return SCVMMTemplateUpload(*args, **kwargs)

        if type_ == 'gce':
            return GoogleCloudTemplateUpload(*args, **kwargs)

        if type_ == 'ec2':
            return EC2TemplateUpload(*args, **kwargs)

        if type_ == 'openshift':
            return OpenshiftTemplateUpload(*args, **kwargs)


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)

    provider_group = parser.add_mutually_exclusive_group(required=True)
    provider_group.add_argument(
        '--provider-type', dest='provider_type', choices=PROVIDER_TYPES,
        help='Provider type')
    provider_group.add_argument(
        '--provider', nargs='+', dest='provider',
        help='Specific providers list')

    parser.add_argument(
        '--stream', nargs='+', dest='stream',
        help='CFME stream template to deploy(downstream-59z, upstream_stable etc). '
             'Please check the cfme_data file for current streams.')
    parser.add_argument(
        '--stream-url', dest='stream_url',
        help='URL for the stream build. Please use with --stream.')
    parser.add_argument(
        '--image-url', dest='image_url',
        help='URL for the image file to be uploaded. Please use with --stream.')
    parser.add_argument(
        '--provider-data', dest='provider_data',
        help='Local yaml file path, to use instead of conf/cfme_data. '
             'Useful for template upload/deploy by non-CFMEQE.')
    parser.add_argument(
        '--template-name', dest='template_name',
        help='Set the name of the template')
    parser.add_argument(
        '--print-name-only', dest='print_name_only', action="store_true",
        help='Only print the template name that will be generated without actually running it.')

    return parser.parse_known_args()


def get_image_url(stream, upload_url):
    if stream in ALL_STREAMS:
        image_url = ALL_STREAMS[stream]
    elif upload_url:
        image_url = upload_url
    else:
        logger.error('Cannot find image URL for stream: {}'.format(stream))
        raise TemplateUploadException("Cannot find image URL.")
    return image_url


def prepare_provider_data(custom_data):
    """ Saves custom provider_data"""
    if custom_data is not None:
        with open(custom_data, 'r') as f:
            local_datafile = f.read()

        with open(path.conf_path.strpath + '/provider_data.yaml', 'w') as cf:
            cf.write(local_datafile)

        return cfme.utils.conf.provider_data


def check_args(cmd_args):
    if cmd_args.stream_url and not cmd_args.stream:
        logger.warning("Please provide stream name with --stream")
        return False

    return True


if __name__ == '__main__':
    cmd_line_args = parse_cmd_line()
    cmd_args = cmd_line_args[0]
    specific_args = cmd_line_args[1]

    if not check_args(cmd_args):
        sys.exit(1)

    template_upload = TemplateUpload()

    provider_data = prepare_provider_data(cmd_args.provider_data)

    if provider_data:
        stream = [provider_data['stream'], ]
        provider_type = provider_data['type']
    else:
        stream = cmd_args.stream
        provider_type = cmd_args.provider_type

    if not provider_type or cmd_args.provider:
        provider_types = PROVIDER_TYPES
    elif provider_type in PROVIDER_TYPES:
        provider_types = [provider_type, ]
    else:
        logger.error('Template upload for %r is not implemented yet.', provider_type)
        sys.exit(1)

    if cmd_args.stream_url:
        streams = {stream: cmd_args.stream_url}
    elif stream:
        streams = cmd_args.stream
    else:
        streams = ALL_STREAMS

    thread_queue = []
    for stream in streams:
        stream_url = ALL_STREAMS.get(stream)
        image_url = cmd_args.image_url

        if not cmd_args.template_name:
            template_name = TemplateName(stream_url).template_name
        else:
            template_name = "{}-{}".format(cmd_args.template_name, stream)

        if cmd_args.print_name_only:
            logger.info("%s Template name: %s", stream, template_name)
            continue

        for provider_type in provider_types:
            providers = list_provider_keys(provider_type)

            if cmd_args.provider:
                providers = filter(lambda x: x in providers, cmd_args.provider)

            for provider in providers:
                if provider not in list_provider_keys(provider_type):
                    continue

                template_kwargs = {
                    'stream': stream,
                    'stream_url': stream_url,
                    'image_url': cmd_args.image_url,
                    'template_name': template_name,
                    'provider_data': provider_data,
                    'provider': provider,
                    'cmd_line_args': specific_args
                }

                # Using factory to obtain needed class
                uploader = template_upload.factory(provider_type, **template_kwargs)

                if uploader.template_upload_data.get('block_upload'):
                    logger.info("{}:{} Skipped due to block upload.".format(
                        uploader.log_name, provider))
                    continue

                thread = Thread(target=uploader.main)
                thread.daemon = True
                thread_queue.append(thread)
                thread.start()

    for thread in thread_queue:
        thread.join()
