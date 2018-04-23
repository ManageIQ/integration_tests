import os
import re

from cfme.utils.log import logger
from cfme.utils.template.base import ProviderTemplateUpload, log_wrap
from cfme.utils.wait import wait_for


class EC2TemplateUpload(ProviderTemplateUpload):
    log_name = 'EC2'
    provider_type = 'ec2'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*ec2[^"\'>]*)')

    @property
    def bucket_name(self):
        return self.provider_data.get('upload_bucket_name', 'cfme-template-upload')

    @property
    def file_path(self):
        return os.path.abspath(self.image_name)

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
