import re

from cfme.utils.log import logger
from cfme.utils.template.base import ProviderTemplateUpload, log_wrap


class GoogleCloudTemplateUpload(ProviderTemplateUpload):
    provider_type = 'gce'
    log_name = 'GCE'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*gce[^"\'>]*)')

    @property
    def bucket_name(self):
        return self.from_template_upload('template_upload_gce').get('bucket_name')

    def get_creds(self, creds_type=None, **kwargs):
        host_default = self.from_credentials('host_default')
        creds = {
            'hostname': self.from_template_upload('template_upload_ec2').get('aws_cli_tool_client'),
            'username': host_default['username'],
            'password': host_default['password']
        }
        return creds

    @log_wrap("download image to cli_tool_client")
    def download_image(self):
        # Check if file exists already:
        if self.execute_ssh_command('ls -1 /var/tmp/templates/{}'.format(self.image_name)).success:
            return True

        # Target directory setup
        if not self.execute_ssh_command('mkdir -p /var/tmp/templates/').success:
            return False

        # Clean downloads directory
        if not self.execute_ssh_command('rm -f /var/tmp/templates/*.gz').success:
            return False

        # Download file to cli-tool-client
        if not self.execute_ssh_command('cd /var/tmp/templates/; '
                                        'curl -O {}'.format(self.image_url)).success:
            return False

        return True

    @log_wrap("create bucket on cli_tool_client")
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

        elif not self.execute_ssh_command('gsutil cp /var/tmp/templates/{} gs://{}'.format(
                self.image_name, self.bucket_name)).success:
            return False

        return True

    @log_wrap("create template from image")
    def create_template(self):
        image = self.mgmt.get_file_from_bucket(self.bucket_name, self.image_name)
        self.mgmt.create_image(image_name=self.template_name, bucket_url=image['selfLink'])
        return True

    def run(self):
        self.download_image()
        self.create_bucket()
        self.upload_image()
        self.create_template()

    @log_wrap("cleanup")
    def teardown(self):
        self.mgmt.delete_file_from_bucket(self.bucket_name, self.image_name)
        self.execute_ssh_command('rm -f /var/tmp/templates/{}'.format(self.image_name))
