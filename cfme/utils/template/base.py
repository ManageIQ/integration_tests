from contextlib import closing
from threading import Lock

from six.moves.urllib.request import urlopen
from six.moves.urllib.error import URLError

from fauxfactory import gen_alphanumeric

from cfme.utils import trackerbot
from cfme.utils.conf import cfme_data, credentials
from cfme.utils.log import logger
from cfme.utils.providers import get_mgmt
from cfme.utils.ssh import SSHClient
from cfme.utils.wait import wait_for

NUM_OF_TRIES = 3
lock = Lock()


class TemplateUploadException(Exception):
    """ Raised on template upload errors"""
    pass


def log_wrap(process_message):
    def decorate(func):
        def call(*args, **kwargs):
            log_name = args[0].log_name
            provider = args[0].provider
            template_name = args[0].template_name
            logger.info("(template-upload) [%s:%s:%s] BEGIN %s",
                        log_name, provider, template_name, process_message)
            result = func(*args, **kwargs)
            if result:
                logger.info("(template-upload) [%s:%s:%s] END %s",
                            log_name, provider, template_name, process_message)
            else:
                logger.error("(template-upload) [%s:%s:%s] FAIL %s",
                             log_name, provider, template_name, process_message)
            return result

        return call

    return decorate


class ProviderTemplateUpload(object):
    """ Base class for template management.

    Class variables:
        :var provider_type: type of initiated provider -- to be removed
        :var log_name: string to be displayed in logs.
        :var image_patters: regex to be matched when stream URL is used
    """
    provider_type = None
    log_name = None
    image_pattern = None

    def __init__(self, stream=None, provider=None, template_name=None,
                 cmd_line_args=None, **kwargs):
        """
        Required parameters:
            :param stream: name of stream
            :param provider: name of provider
            :param template_name: name of template to use

        Optional parameters:
            :param stream_url: custom URL to image directory of a stream
            :param image_url: custom URL to exact image file
            :param provider_data: custom AttrDict with provider data

        Default values for custom parameters:
            :param stream_url: cfme_data.basic_info.cfme_images_url[stream]
            :param image_url: parsed with regex from stream_url web page
            :param provider_data: cfme_data.management_systems[provider]
        """
        self._stream_url = kwargs.get('stream_url')
        self._image_url = kwargs.get('image_url')
        self._provider_data = kwargs.get('provider_data')

        self._cmd_line_args = cmd_line_args

        self.stream = stream
        self.provider = provider
        self.template_name = template_name

        self.kwargs = kwargs

    @property
    def stream_url(self):
        """ Returns URL to image directory of a stream.

        Example output:
            http://hostname.redhat.com/builds/cfme/version/stable/

        Default value:
            stored in cfme_data.basic_info.cfme_images_url[stream] for known streams
        """
        urls = cfme_data.basic_info.cfme_images_url

        if self._stream_url:
            return self._stream_url
        elif self.stream in urls:
            return urls[self.stream]
        else:
            logger.error("Stream %s is not listed in cfme_data. "
                         "Please specify stream URL with --stream_url", self.stream)
            raise TemplateUploadException("Cannot get stream URL.")

    @property
    def image_url(self):
        """ Returns URL to exact image file.

        Example output:
            http://hostname.redhat.com/builds/cfme/version/stable/cfme-type-version.x86_64.vhd

        Default value:
            browses stream_url for images and matches them to image_pattern regex
        """
        if not self._image_url:
            try:
                with closing(urlopen(self.stream_url)) as stream_dir:
                    string_from_url = stream_dir.read()
            except URLError as e:
                logger.error("Cannot get image URL from %s: %s", self.stream_url, e.reason.strerror)
                raise TemplateUploadException("Cannot get image URL.")
            else:
                image_name = self.image_pattern.findall(string_from_url)
                if len(image_name):
                    return "{}{}".format(self.stream_url, image_name[0])
        return self._image_url

    @property
    def image_name(self):
        """ Returns filename of an image.

        Example output: cfme-type-version.x86_64.vhd
        """
        return self.image_url.split("/")[-1]

    @property
    def mgmt(self):
        """ Returns wrapanapi management system class.

        provider_data has higher priority than provider name.
        """
        if self.provider_data:
            return get_mgmt(self.provider_data)
        elif self.provider:
            return get_mgmt(self.provider)
        else:
            logger.error("Please specify provider or provider_data to retrieve it's mgmt.")
            raise TemplateUploadException("Cannot get_mgmt due to empty data.")

    @property
    def provider_data(self):
        """ Returns AttrDict from cfme_data[management_systems][provider]."""
        if not self._provider_data:
            return cfme_data.management_systems[self.provider]
        return self._provider_data

    @property
    def template_upload_data(self):
        """ Returns provider_data[provider][template_upload] if exists."""
        return self.provider_data.get('template_upload', {})

    @staticmethod
    def from_template_upload(key):
        return cfme_data.template_upload.get(key, {})

    def from_credentials(self, key):
        return credentials[self.provider_data[key]]

    def get_creds(self, creds_type=None, **kwargs):
        """ Returns credentials mapping."""

        # TODO it in a different way
        if creds_type == 'ssh' and "ssh_creds" in self.provider_data.keys():
            creds = self.provider_data['ssh_creds']
        else:
            creds = self.provider_data['credentials']

        ssh_creds = {
            'hostname': kwargs.get('hostname') or self.provider_data['hostname'],
            'username': kwargs.get('username') or credentials[creds]['username'],
            'password': kwargs.get('password') or credentials[creds]['password']
        }

        return ssh_creds

    def execute_ssh_command(self, command, creds=None, **kwargs):
        """ Wraps SSHClient to get credentials and execute given command."""
        if not creds:
            creds = self.get_creds(creds_type='ssh', **kwargs)
        with SSHClient(**creds) as ssh_client:
            return ssh_client.run_command(command, **kwargs)

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
    def track_template(self):
        trackerbot.trackerbot_add_provider_template(self.stream, self.provider, self.template_name)
        return True

    @log_wrap("deploy template")
    def deploy_template(self):
        deploy_args = {
            'provider': self.provider,
            'vm_name': 'test_{}_{}'.format(self.template_name, gen_alphanumeric(8)),
            'template': self.template_name,
            'deploy': True,
            'network_name': self.provider_data['network']}

        self.mgmt.deploy_template(**deploy_args)
        return True

    @log_wrap("template upload script")
    def main(self):
        try:

            if self.provider_type != 'openshift' and \
                    self.mgmt.does_template_exist(self.template_name):
                logger.info("(template-upload) [%s:%s:%s] Template already exists",
                            self.log_name, self.provider, self.template_name)
            else:
                wait_for(self.decorated_run, fail_condition=False, delay=5, logger=None)

                if not self._provider_data:
                    self.track_template()

            if self._provider_data and self.mgmt.does_template_exist(self.template_name):
                self.deploy_template()

            return True

        except TemplateUploadException:
            return False

        finally:
            self.teardown()
