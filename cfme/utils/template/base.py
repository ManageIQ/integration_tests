import os
import re


from contextlib import closing
from os import path
from threading import Lock
from zipfile import ZipFile
from cached_property import cached_property
from fauxfactory import gen_alphanumeric
from glanceclient import Client
from six.moves.urllib.request import urlopen
from six.moves.urllib.error import URLError
from six.moves.urllib import request


from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.containers.provider.openshift import OpenshiftProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.utils.path import project_path
from cfme.utils import trackerbot
from cfme.utils.conf import cfme_data, credentials
from cfme.utils.log import logger
from cfme.utils.providers import get_mgmt
from cfme.utils.ssh import SSHClient

NUM_OF_TRIES = 3
lock = Lock()

PROVIDER_TYPES = [p.type_name
                  for p in [EC2Provider, GCEProvider, OpenshiftProvider, OpenStackProvider,
                            RHEVMProvider, SCVMMProvider, VMwareProvider]]
ALL_STREAMS = cfme_data['basic_info']['cfme_images_url']


class TemplateUploadException(Exception):
    """ Raised on template upload errors"""
    pass


def log_wrap(process_message):
    def decorate(func):
        def call(*args, **kwargs):
            log_name = args[0].log_name
            provider_key = args[0].provider_key
            template_name = args[0].template_name
            logger.info("(template-upload) [%s:%s:%s] BEGIN %s",
                        log_name, provider_key, template_name, process_message)
            result = func(*args, **kwargs)
            if result:
                logger.info("(template-upload) [%s:%s:%s] END %s",
                            log_name, provider_key, template_name, process_message)
            else:
                logger.error("(template-upload) [%s:%s:%s] FAIL %s",
                             log_name, provider_key, template_name, process_message)
            return result

        return call

    return decorate


class ProviderTemplateUpload(object):
    """ Base class for template management.

    Class variables:
        :var provider_type: type of initiated provider -- to be removed
        :var log_name: string to be displayed in logs.
        :var image_pattern: regex to be matched when stream URL is used
    """
    provider_type = None
    log_name = None
    image_pattern = None

    def __init__(self, provider_key, stream, template_name, image_url=None, **kwargs):
        """
        Required parameters:
            :param stream: name of stream
            :param provider_key: key of provider in yaml
            :param template_name: name of template to use
            :param image_url: custom URL to image directory of a stream, defaults to stream/stable

        Default values for custom parameters:
            :param image_url: cfme_data.basic_info.cfme_images_url[stream]
        """
        self.stream = stream
        self.provider_key = provider_key
        self.template_name = template_name
        self.glance_key = kwargs.get('glance_key')  # available for multiple provider type
        self.image_url = image_url  # TODO default
        self._unzipped_file = None

    @property
    def stream_url(self):
        """ Returns URL to image directory of a stream.

        Example output:
            http://hostname.redhat.com/builds/cfme/version/stable/

        Default value:
            stored in cfme_data.basic_info.cfme_images_url[stream] for known streams
        """
        urls = cfme_data.basic_info.cfme_images_url

        if self.stream in urls:
            return urls[self.stream]
        else:
            logger.error("Stream %s is not listed in cfme_data. "
                         "Please specify stream with --stream", self.stream)
            raise TemplateUploadException("Cannot get stream URL.")

    @property
    def raw_image_url(self):
        """ Returns URL to exact image file.

        Example output:
            http://hostname.redhat.com/builds/cfme/version/stable/cfme-type-version.x86_64.vhd

        Default value:
            browses stream_url for images and matches them to image_pattern regex
        """
    # TODO rework to pull default image for stream URL
        try:
            with closing(urlopen(self.image_url)) as image_dir:
                string_from_url = image_dir.read()
        except URLError as e:
            logger.error("Cannot get image URL from %s: %s", self.image_url, e.reason.strerror)
            raise TemplateUploadException("Cannot get image URL.")
        else:
            image_name = self.image_pattern.findall(string_from_url)
            if len(image_name):
                # return 0th element of image_name, likely multiple formats for same provider type
                return '/'.join([self.image_url, image_name[0]])  # TODO support multiple formats

    @property
    def image_name(self):
        """ Returns filename of an downloaded or unzipped image.

        Example output: cfme-type-version-x86_64-vhd
        """
        return self._unzipped_file or self.raw_image_url.split("/")[-1]

    @property
    def local_file_path(self):
        return project_path.join(self.image_name).strpath

    @property
    def mgmt(self):
        """ Returns wrapanapi management system class.

        """
        return get_mgmt(self.provider_key)

    @property
    def provider_data(self):
        """ Returns AttrDict from cfme_data[management_systems][provider]."""
        return cfme_data.management_systems[self.provider_key]

    @property
    def template_upload_data(self):
        """ Returns yaml provider's [template_upload] if exists."""
        return self.provider_data.get('template_upload', {})

    @cached_property
    def temp_template_name(self):
        return 'raw-{}'.format(self.image_name)[:40]  # rhevm template name length for <4.2

    @cached_property
    def temp_vm_name(self):
        return 'raw-vm-{}'.format(self.template_name)

    @cached_property
    def creds(self):
        return credentials[self.provider_data['credentials']]

    @cached_property
    def ssh_client_args(self):
        """ Returns credentials + hostname for ssh client auth."""
        cred_key = self.provider_data.get('ssh_creds') or self.provider_data['credentials']
        return {'hostname': self.provider_data['hostname'],
                'username': credentials[cred_key]['username'],
                'password': credentials[cred_key]['password']}

    @cached_property
    def tool_client_args(self):
        tool_data = self.from_template_upload('tool_client')
        return {'hostname': tool_data.hostname,
            'username': credentials[tool_data['credentials']].username,
            'password': credentials[tool_data['credentials']].password}

    @staticmethod
    def from_template_upload(key):
        return cfme_data.template_upload.get(key, {})

    def execute_ssh_command(self, command, client_args=None):
        """ Wraps SSHClient to get credentials and execute given command."""
        with SSHClient(**(client_args or self.ssh_client_args)) as ssh_client:
            return ssh_client.run_command(command)

    def setup(self):
        pass

    def run(self):
        raise NotImplementedError("run is not implemented")

    @log_wrap("run upload template")
    def decorated_run(self):
        return self.run()

    def teardown(self):
        pass

    @log_wrap("add template to trackerbot")
    def track_template(self, **kwargs):
        trackerbot.trackerbot_add_provider_template(self.stream,
                                                    self.provider_key,
                                                    self.template_name,
                                                    **kwargs)
        return True

    @log_wrap("deploy template")
    def deploy_template(self):
        deploy_args = {
            'vm_name': 'test_{}_{}'.format(self.template_name, gen_alphanumeric(8)),
            'template': self.template_name,
            'deploy': True,
            'network_name': self.provider_data['network']
        }
        # TODO: change after openshift wrapanapi refactor
        if self.provider_type == 'openshift':
            self.mgmt.deploy_template(**deploy_args)
        else:
            template = self.mgmt.get_template(deploy_args['template'])
            template.deploy(**deploy_args)
        return True

    @log_wrap("download image locally")
    def download_image(self):
        suffix = re.compile(
            r'^.*?[.](?P<ext>tar\.gz|tar\.bz2|\w+)$').match(self.image_name).group('ext')
        print(self.image_name, self.local_file_path)
        # Check if file exists already:
        if path.isfile(self.local_file_path):
            logger.info('Local image found, skipping download: %s', self.local_file_path)
            if suffix not in ['zip']:
                return True
        else:
            # Download file to cli-tool-client
            try:
                request.urlretrieve(self.raw_image_url, self.local_file_path)
            except URLError:
                logger.exception('Failed download of image using urllib')
                return False

        # Unzips image  when suffix is zip or tar.gz and then changes image name to extracted one.
        # For EC2 and SCVMM images is zip used and for GCE is tar.gz used.

        archive_path = self.image_name
        try:
            if suffix == 'zip':
                archive = ZipFile(archive_path)
                zipinfo = archive.infolist()
                self._unzipped_file = zipinfo[0].filename
            else:
                return True
            if path.isfile(self.image_name):
                os.remove(self.image_name)
            logger.info('Image archived - unzipping as : %s', self._unzipped_file)
            archive.extractall()
            archive.close()
            # remove the archive
            os.remove(archive_path)
            return True
        except Exception:
            logger.exception("{} archive unzip failed.".format(suffix))
            return False

    @log_wrap('add template to glance')
    def glance_upload(self):
        """Push template to glance server
        if session is true, use keystone auth session from self.mgmt

        if session is false, use endpoint directly:
        1. download template to NFS mounted share on glance server via ssh+wget
        2. create image record in glance's db
        3. update image record with the infra-truenas webdav URL
        """
        if self.provider_type == 'openstack':
            # This means its a full openstack provider, and we should use its mgmt session
            client_kwargs = dict(session=self.mgmt.session)
        else:
            # standalone glance server indirectly hosting image to be templatized
            client_kwargs = dict(endpoint=self.from_template_upload(self.glance_key).get('url'))
        client = Client(version='2', **client_kwargs)
        if self.image_name in [i.name for i in client.images.list()]:
            logger.info('Image "%s" already exists on %s, skipping glance_upload',
                        self.image_name, self.provider_key)
            return True

        glance_image = client.images.create(
            name=self.template_name if self.provider_type == 'openstack' else self.image_name,
            container_format='bare',
            disk_format='qcow2',
            visibility='public')
        if self.template_upload_data.get('remote_location'):
            # add location for image on standalone glance
            client.images.add_location(glance_image.id, self.raw_image_url, {})
        else:
            if self.download_image():
                client.images.upload(glance_image.id, open(self.local_file_path, 'rb'))
            else:
                return False
        return True

    @log_wrap("template upload script")
    def main(self):
        try:
            if self.provider_type != 'openshift' and self.mgmt.does_template_exist(
                    self.template_name):
                logger.info("(template-upload) [%s:%s:%s] Template already exists",
                            self.log_name, self.provider_key, self.template_name)
            else:
                if self.decorated_run():
                    # openshift run will call track_template since it needs custom_data kwarg
                    if self.provider_type != 'openshift':
                        self.track_template()
            return True

        except TemplateUploadException:
            logger.exception('TemplateUploadException, failed upload')
            return False
        except Exception:
            logger.exception('non-TemplateUploadException, failed interaction with provider')
            return False

        finally:
            self.teardown()
