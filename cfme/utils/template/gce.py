import re

from cfme.utils.log import logger
from cfme.utils.template.base import BaseTemplateUpload

from cfme.utils.conf import cfme_data, credentials


class GoogleCloudTemplateUpload(BaseTemplateUpload):
    provider_type = 'gce'
    log_name = 'GCE'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*gce[^"\'>]*)')
    bucket_name = 'cfme-images'

    def get_creds(self, creds_type=None, **kwargs):
        creds = {'hostname': cfme_data.template_upload.template_upload_ec2['aws_cli_tool_client'],
                 'username': credentials.host_default['username'],
                 'password': credentials.host_default['password']}
        return creds

    def download_image(self):
        # Check if file exists already:
        res = self.execute_ssh_command('ls -1 /var/tmp/templates/{}'.format(self.image_name))
        if res.success:
            return True

        logger.info('INFO: Preparing cli-tool-client machine for download...')
        # Target directory setup
        assert self.execute_ssh_command('mkdir -p /var/tmp/templates/').success
        # This should keep the downloads directory clean
        assert self.execute_ssh_command('rm -f /var/tmp/templates/*.gz').success

        logger.info('INFO: Downloading file to cli-tool-client.')
        assert self.execute_ssh_command(
            'cd /var/tmp/templates/; curl -O {}'.format(self.image_url)).success

    def create_bucket(self):
        logger.info('GCE:%s Checking if bucket already exists.', self.provider)
        if not self.mgmt.bucket_exists(self.bucket_name):
            logger.info('GCE:%s Creating bucket %s.', self.provider, self.bucket_name)
            self.mgmt.create_bucket(self.bucket_name)
        else:
            logger.info('GCE:%s Bucket %s already exists.', self.provider, self.bucket_name)

    def upload_image(self):
        logger.info('GCE:%s Checking if file on bucket already.', self.provider)

        if not self.mgmt.get_file_from_bucket(self.bucket_name, self.image_name):
            logger.info('GCE:%s Uploading %s to bucket.', self.provider, self.image_name)
            result = self.execute_ssh_command(
                'gsutil cp /var/tmp/templates/{} gs://{}'.format(self.image_name, self.bucket_name))
            assert result.success
        else:
            logger.info('GCE:%s File %s already exists on bucket.', self.provider, self.image_name)

    def create_template(self):
        logger.info('GCE:%s Creating template %s from bucket %s.',
                    self.provider, self.template_name, self.bucket_name)
        image = self.mgmt.get_file_from_bucket(self.bucket_name, self.image_name)
        self.mgmt.create_image(image_name=self.template_name, bucket_url=image['selfLink'])
        logger.info('GCE:%s Successfully created image %s from bucket %s',
                    self.provider, self.template_name, self.bucket_name)

    def run(self):
        self.download_image()
        self.create_bucket()
        self.upload_image()
        self.create_template()

    def teardown(self):
        self.mgmt.delete_file_from_bucket(self.bucket_name, self.image_name)
        self.execute_ssh_command('rm -f /var/tmp/templates/{}'.format(self.image_name))
