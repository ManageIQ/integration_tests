"""
NOT TESTED YET
"""

import re
import os

from cfme.utils.log import logger
from cfme.utils.template.base import ProviderTemplateUpload, log_wrap


class OpenshiftTemplateUpload(ProviderTemplateUpload):
    log_name = "OPENSHIFT"
    provider_type = "openshift"
    image_pattern = re.compile(r'<a href="?\'?(openshift-pods/*)')

    @property
    def upload_folder(self):
        return self.from_template_upload('template_upload_openshift').get('upload_folder')

    @property
    def destination_directory(self):
        return os.path.join(self.upload_folder, self.template_name)

    @property
    def main_template(self):
        return os.path.join(self.destination_directory, 'cfme-template.yaml')

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

    def does_template_exist(self):
        check_dir_exists = 'ls -A {}'.format(self.destination_directory)

        result = self.execute_ssh_command(check_dir_exists, creds=self.creds())

        if result.success and result.output:
            return True

    @log_wrap('create destination directory')
    def create_destination_directory(self):
        create_dir_cmd = 'mkdir -p {}'.format(self.destination_directory)

        if self.execute_ssh_command(create_dir_cmd, creds=self.creds()).success:
            return True

    @log_wrap('download template')
    def download_template(self):
        download_cmd = ('wget -q --no-parent --no-directories --reject "index.html*" '
                        '--directory-prefix={} -r {}').format(self.destination_directory,
                                                              self.image_url)

        if self.execute_ssh_command(download_cmd, creds=self.creds()).success:
            return True

    @log_wrap('login to openshift')
    def login_to_oc(self):
        oc_creds = self.creds('oc_creds')
        login_cmd = 'oc login --username={} --password={}'.format(oc_creds['username'],
                                                                  oc_creds['password'])

        if self.execute_ssh_command(login_cmd).success:
            return True

    def get_urls(self):
        get_urls_cmd = ('find {} -type f -name "cfme-openshift-*" '
                        '-exec tail -1 {{}} \;').format(self.destination_directory)

        result = self.execute_ssh_command(get_urls_cmd, creds=self.creds())
        if result.failed:
            return False

        urls = result.output.split()
        for url in urls:
            update_img_cmd = 'docker pull {}'.format(url)

            res_url = self.execute_ssh_command(update_img_cmd, creds=self.creds())
            if res_url.failed:
                return False

        for template in ('cloudforms', self.template_name):
            get_template_cmd = 'oc get template {} --namespace=openshift'.format(template)
            delete_template_cmd = 'oc delete template {} --namespace=openshift'.format(template)

            if self.execute_ssh_command(get_template_cmd, creds=self.creds()).success:
                self.execute_ssh_command(delete_template_cmd, creds=self.creds())

        change_name_cmd = """python -c 'import yaml
data = yaml.safe_load(open("{file}"))
data["metadata"]["name"] = "{new_name}"
yaml.safe_dump(data, stream=open("{file}", "w"))'""".format(new_name=self.template_name,
                                                            file=self.main_template)
        if self.execute_ssh_command(change_name_cmd, creds=self.creds()).failed:
            return False

        create_template_cmd = 'oc create -f {} --namespace=openshift'.format(self.main_template)
        if self.execute_ssh_command(create_template_cmd, creds=self.creds()).failed:
            return False

        return True

    def run(self):
        if 'podtesting' not in self.provider_data.get('tags'):
            logger.info("%s:%s No podtesting tag.", self.log_name, self.provider)
            return

        if self.does_template_exist():
            logger.info("Template already exists.")
            return True

        if not self.create_destination_directory():
            return False

        if not self.download_template():
            return False

        if not self.login_to_oc():
            return False

        if not self.get_urls():
            return False
