import os
import re
import six.moves.urllib.request
import six.moves.urllib.error
import six.moves.urllib.parse

from cfme.utils.log import logger
from cfme.utils.template.base import ProviderTemplateUpload, log_wrap
from cfme.utils.wait import wait_for


class EC2TemplateUpload(ProviderTemplateUpload):
    log_name = 'EC2'
    provider_type = 'ec2'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*ec2[^"\'>]*)')

    def get_creds(self, creds_type=None, **kwargs):
        host_default = self.from_credentials('host_default')
        creds = {
            'hostname': self.from_template_upload('template_upload_ec2').get('aws_cli_tool_client'),
            'username': host_default['username'],
            'password': host_default['password']
        }
        return creds

    @property
    def bucket_name(self):
        return self.provider_data.get('upload_bucket_name', 'cfme-template-upload')

    @property
    def file_path(self):
        return os.path.abspath(self.image_name)

    @log_wrap("download image")
    def download_image(self):
        try:
            u = six.moves.urllib.request.urlopen(self.image_url)
            meta = u.info()
            file_size = int(meta.getheaders("Content-Length")[0])

            if os.path.isfile(self.image_name):

                if file_size == os.path.getsize(self.image_name):
                    logger.info("(template-upload) [%s:%s:%s] Image %s already exists.",
                                self.log_name, self.provider, self.template_name, self.image_name)
                    return True
                os.remove(self.image_name)

            logger.info("(template-upload) [%s:%s:%s] Downloading %s to local directory. Bytes: %d",
                        self.log_name, self.provider, self.template_name, self.image_name,
                        file_size)

            with open(self.image_name, 'wb') as image_file:
                file_size_dl = 0
                block_sz = 8192
                while True:
                    buffer_f = u.read(block_sz)
                    if not buffer_f:
                        break

                    file_size_dl += len(buffer_f)
                    image_file.write(buffer_f)
            return True

        except:
            return False

    @log_wrap("create bucket")
    def create_bucket(self):
        for bucket in self.mgmt.s3_connection.buckets.all():
            if bucket.name == self.bucket_name:
                logger.info("(template-upload) [%s:%s:%s] Bucket %s already exists.",
                            self.log_name, self.provider, self.template_name, self.bucket_name)
                return True

        try:
            self.mgmt.create_s3_bucket(self.bucket_name)
            return True

        except:
            return False

    @log_wrap("upload image to bucket")
    def upload_image(self):
        try:
            self.mgmt.upload_file_to_s3_bucket(self.bucket_name,
                                               file_path=self.file_path,
                                               file_name=self.template_name)
            return True

        except:
            return False

    @log_wrap("import image from bucket")
    def import_image(self):
        try:
            import_task_id = self.mgmt.import_image(s3bucket=self.bucket_name,
                                                    s3key=self.template_name,
                                                    description=self.template_name)

            wait_for(self.mgmt.get_image_id_if_import_completed,
                     func_args=[import_task_id],
                     fail_condition=False,
                     delay=5,
                     timeout='90m',
                     message='Importing image to EC2')

            ami_id = self.mgmt.get_image_id_if_import_completed(import_task_id)
            self.mgmt.copy_image(source_region=self.mgmt.api.region.name,
                                 source_image=ami_id,
                                 image_id=self.template_name)
            self.mgmt.get_template(ami_id).cleanup()
            return True

        except:
            return False

    def run(self):
        if not self.download_image():
            return False

        if not self.create_bucket():
            return False

        if not self.upload_image():
            return False

        if not self.import_image():
            return False

        return True

    @log_wrap("cleanup")
    def teardown(self):
        self.mgmt.delete_objects_from_s3_bucket(bucket_name=self.bucket_name,
                                                object_keys=[self.template_name])
        if os.path.exists(self.file_path):
            os.remove(self.file_path)

        return True
