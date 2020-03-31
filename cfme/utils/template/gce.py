import re
from subprocess import check_call

from cached_property import cached_property

from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.template.base import log_wrap
from cfme.utils.template.base import ProviderTemplateUpload


class GoogleCloudTemplateUpload(ProviderTemplateUpload):
    provider_type = 'gce'
    log_name = 'GCE'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*gce[^"\'>]*)')
    blocked_streams = ['upstream', 'downstream-511z']

    @property
    def bucket_name(self):
        return self.from_template_upload('template_upload_gce').get('bucket_name')

    @cached_property
    def awstool_client_args(self):
        ec2_template_upload = self.from_template_upload('template_upload_ec2')
        creds = {
            'hostname': ec2_template_upload.get('aws_cli_tool_client'),
            'username': credentials[ec2_template_upload['ovf_tool_creds']].username,
            'password': credentials[ec2_template_upload['ovf_tool_creds']].password
        }
        return creds

    @log_wrap("download image locally")
    def download_image(self):
        # Check if file exists already:
        if check_call('ls', self.local_file_path) == 0:
            logger.info('Local image found, skipping download: %s', self.local_file_path)
            return True

        # Download file to cli-tool-client
        return check_call('curl',
                          f'--output {self.local_file_path}',
                          self.raw_image_url) == 0

    @log_wrap("create bucket on GCE")
    def create_bucket(self):
        if not self.mgmt.bucket_exists(self.bucket_name):
            self.mgmt.create_bucket(self.bucket_name)
        else:
            logger.info('(template-upload) [%s:%s:%s] Bucket %s already exists.',
                        self.log_name, self.provider, self.template_name, self.bucket_name)
        return True

    @log_wrap("upload image to bucket")
    def upload_image(self):
        if self.mgmt.get_file_from_bucket(self.bucket_name, self.image_name):
            logger.info('(template-upload) [%s:%s:%s] File %s already exists on bucket.',
                        self.log_name, self.provider, self.template_name, self.image_name)

        else:
            self.mgmt.upload_file_to_bucket(self.bucket_name, self.local_file_path)

        return True

    @log_wrap("create template from image")
    def create_template(self):
        image = self.mgmt.get_file_from_bucket(self.bucket_name, self.image_name)
        self.mgmt.create_image(image_name=self.template_name, bucket_url=image['selfLink'])
        return True

    def run(self):
        if not self.download_image():
            return False

        if not self.create_bucket():
            return False

        if not self.upload_image():
            return False

        if not self.create_template():
            return False

    @log_wrap("cleanup")
    def teardown(self):
        self.mgmt.delete_file_from_bucket(self.bucket_name, self.image_name)
        self.execute_ssh_command(f'rm -f /var/tmp/templates/{self.image_name}')
