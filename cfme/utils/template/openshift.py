import re

from cfme.utils.log import logger
from cfme.utils.template.base import BaseTemplateUpload


class OpenshiftTemplateUpload(BaseTemplateUpload):
    log_name = "OPENSHIFT"
    provider_type = "openshift"
    image_pattern = re.compile(r'<a href="?\'?(openshift-pods/*)')

    def run(self):
        if 'podtesting' not in self.provider_data.get('tags'):
            logger.info("%s:%s No podtesting tag.", self.log_name, self.provider)
            return

    @property
    def upload_folder(self):
        return self.from_template_upload('template_upload_openshift').get('upload_folder')

    def creds(self, creds_type='ssh_creds'):
        if self._provider_data:
            creds = self._provider_data
        elif creds_type == 'ssh_creds':
            creds = self.from_credentials('ssh_creds')
        elif creds_type == 'oc_creds':
            creds = self.from_credentials('credentials')
        else:
            raise Exception("Credentials not found.")

        kwargs = {'hostname': self.provider_data['hostname'],
                  'username': creds['username'],
                  'password': creds['password']}

        return kwargs
