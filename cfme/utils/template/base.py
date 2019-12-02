import hashlib
import os
import re
from contextlib import closing
from os import path
from threading import Lock
from urllib import request
from urllib.error import URLError
from urllib.request import urlopen
from zipfile import ZipFile

from cached_property import cached_property
from fauxfactory import gen_alphanumeric
from glanceclient import Client

from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.containers.provider.openshift import OpenshiftProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import trackerbot
from cfme.utils.conf import cfme_data
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.net import wait_pingable
from cfme.utils.path import project_path
from cfme.utils.providers import get_mgmt
from cfme.utils.ssh import SSHClient
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

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
    blocked_streams = []

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
                string_from_url = image_dir.read().decode('utf-8')
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
    def raw_vm_ssh_client_args(self):
        """ Returns credentials + hostname for ssh client auth for a temp_vm."""
        try:
            vm_ip = wait_pingable(self._vm_mgmt, wait=300)
        except TimedOutError:
            msg = 'Timed out waiting for reachable raw VM IP'
            logger.exception(msg)
            raise TemplateUploadException(msg)

        return {'hostname': vm_ip,
                'username': credentials['ssh']['username'],
                'password': credentials['ssh']['password']}

    @cached_property
    def tool_client_args(self):
        tool_data = self.from_template_upload('tool_client')
        return {'hostname': tool_data.hostname,
            'username': credentials[tool_data['credentials']].username,
            'password': credentials[tool_data['credentials']].password}

    @cached_property
    def _vm_mgmt(self):
        return self.mgmt.get_vm(self.temp_vm_name)

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
        """Call trackerbot API to create the providertemplate record

        Returns:
            None - when template already existed
            bool - true when record added, false when record add fails (without exception)
        """
        result = trackerbot.add_provider_template(
            kwargs.pop('stream', self.stream),
            kwargs.pop('provider_key', self.provider_key),
            kwargs.pop('template_name', self.template_name),
            **kwargs
        )
        if result:
            logger.info('Added trackerbot record: [%s] / [%s] / [%s]',
                        self.stream, self.provider_key, self.template_name)
        elif result is None:
            logger.warning('Trackerbot record already existed: [%s] / [%s] / [%s]',
                           self.stream, self.provider_key, self.template_name)
        else:
            logger.error('FAILED adding trackerbot record:  [%s] / [%s] / [%s]',
                         self.stream, self.provider_key, self.template_name)

        return result

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

    @log_wrap("checksum verification")
    def checksum_verification(self):
        # Download checksum from url
        checksum = None
        try:
            response = request.urlopen('{}/SHA256SUM'.format(self.image_url))
            checksums = response.read().decode('utf-8')
            for line in checksums.split("\n"):
                if self.image_name in line:
                    checksum = line.strip().split()[0]
        except URLError:
            logger.warn('Failed download of checksum using urllib')
        if not checksum:
            logger.warn('Failed to get checksum of image from url')
        else:
            # Get checksum of downloaded file
            sha256 = hashlib.sha256()
            image_sha256 = None
            try:
                with open(self.image_name, 'rb') as f:
                    for block in iter(lambda: f.read(65536), b''):
                        sha256.update(block)
                image_sha256 = sha256.hexdigest()
            except Exception:
                logger.warn('Failed to get checksum of image')
            if image_sha256 and not checksum == image_sha256:
                logger.exception('Local image checksum does not match checksum from url')
                return False
            else:
                logger.info('Local image checksum matches checksum from url')
                return True

    @log_wrap("download image locally")
    def download_image(self):
        ARCHIVE_TYPES = ['zip']
        suffix = re.compile(
            r'^.*?[.](?P<ext>tar\.gz|tar\.bz2|\w+)$').match(self.image_name).group('ext')
        # Check if file exists already:
        if path.isfile(self.image_name):
            if self.checksum_verification():
                logger.info('Local image found, skipping download: %s', self.local_file_path)
                if suffix not in ARCHIVE_TYPES:
                    return True
            else:
                os.remove(self.local_file_path)

        if not path.isfile(self.image_name):
            # Download file to cli-tool-client
            try:
                request.urlretrieve(self.raw_image_url, self.local_file_path)
            except URLError:
                logger.exception('Failed download of image using urllib')
                return False

        self.checksum_verification()

        # Unzips image  when suffix is zip or tar.gz and then changes image name to extracted one.
        # For EC2 and SCVMM images is zip used and for GCE is tar.gz used.

        archive_path = self.image_name
        if suffix not in ARCHIVE_TYPES:
            return True
        else:
            if suffix == 'zip':
                try:
                    archive = ZipFile(archive_path)
                    zipinfo = archive.infolist()
                    self._unzipped_file = zipinfo[0].filename
                except Exception:
                    logger.exception("Getting information of {} archive failed.".format(
                        self.image_name))
                    return False

                if path.isfile(self.image_name):
                    try:
                        os.remove(self.image_name)
                    except Exception:
                        logger.exception("Deleting previously unpacked file {} failed.".format(
                            self.image_name))
                        return False
                logger.info("Image archived - unpacking as : {}".format(self._unzipped_file))
                try:
                    archive.extractall()
                    archive.close()
                    # remove the archive
                    os.remove(archive_path)
                    return True
                except Exception:
                    logger.exception("{} archive unpacked failed.".format(suffix))
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
                        self.image_name, self.glance_key)
            return True

        glance_image = client.images.create(
            name=self.image_name,
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

    @log_wrap('clean out default setup of a ManageIQ appliance')
    def manageiq_cleanup(self):
        """Clean out the default setup of a ManageIQ appliance
            Based on:
                https://gist.github.com/carbonin/a25b84efca2e6b3c3f91b673821a22c8
        """

        def check_appliance_init(client_args):
            app_init_complete_check = ['Active: inactive (dead)', 'Loaded: loaded',
                                       'Started Initialize Appliance Database']
            try:
                out = self.execute_ssh_command('systemctl status appliance-initialize',
                                               client_args=client_args)
                return all(check in out.output for check in app_init_complete_check)
            except Exception:
                # Have seen instances where IP is resolvable but SSH connect failed.
                logger.info('SSH connection failed, trying again')
                return False

        upstream_cleanup = [
            "/var/www/miq/vmdb/REGION",
            "/var/www/miq/vmdb/GUID",
            "/var/www/miq/vmdb/certs/*",
            "/var/www/miq/vmdb/config/database.yml",
            "/var/lib/pgsql/data/*"
        ]

        upstream_services = [
            "systemctl stop evmserverd",
            "systemctl disable evmserverd",
            "systemctl stop postgresql.service",
            "systemctl disable postgresql.service",
            "systemctl disable appliance-initialize"
        ]
        # Get SSH Client args
        client_args = self.raw_vm_ssh_client_args
        # Check to make sure appliance-initialization has run
        wait_for(func=check_appliance_init,
                 func_args=[client_args],
                 fail_condition=False,
                 delay=5,
                 timeout=300,
                 message='Waiting for appliance-initialization to complete')
        for service in upstream_services:
            self.execute_ssh_command('{}'.format(service), client_args=client_args)
        for cleanup in upstream_cleanup:
            self.execute_ssh_command('rm -rf {}'.format(cleanup), client_args=client_args)

        check_pgsql = self.execute_ssh_command('ls /var/lib/pgsql/data/', client_args=client_args)

        if not check_pgsql.output:
            logger.info('Finished cleaning out the default setup of a ManageIQ appliance')
            return True
        else:
            logger.error('Cleaning the default setup of a ManageIQ appliance has failed')
            return False

    @log_wrap("template upload script")
    def main(self):
        track = False
        teardown = False
        try:
            if self.stream in self.blocked_streams:
                logger.info('This stream (%s) is blocked for the given provider type, %s',
                            self.stream, self.provider_type)
                return True
            if self.provider_type != 'openshift' and self.mgmt.does_template_exist(
                    self.template_name):
                logger.info("(template-upload) [%s:%s:%s] Template already exists",
                            self.log_name, self.provider_key, self.template_name)
                track = True
            else:
                teardown = True
                if self.decorated_run():
                    track = True
            if track and self.provider_type != 'openshift':
                # openshift run will call track_template since it needs custom_data kwarg
                self.track_template()

            return True

        except TemplateUploadException:
            logger.exception('TemplateUploadException, failed upload')
            return False
        except Exception:
            logger.exception('non-TemplateUploadException, failed interaction with provider')
            return False

        finally:
            if teardown:
                self.teardown()
