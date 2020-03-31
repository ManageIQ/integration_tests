import os
import re

from cfme.utils.log import logger
from cfme.utils.template.base import log_wrap
from cfme.utils.template.base import ProviderTemplateUpload


class OpenshiftTemplateUpload(ProviderTemplateUpload):
    log_name = "OPENSHIFT"
    provider_type = "openshift"
    image_pattern = re.compile(r'<a href="?\'?(openshift-pods/*)')
    blocked_streams = ['upstream', 'downstream-511z']

    template_filenames = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tags = None

    @property
    def tags(self):
        return self._tags

    @tags.setter
    def tags(self, tags):
        self._tags = tags

    @property
    def templates(self):
        return [
            {'filename': 'cfme-template.yaml',
             'name': self.template_name},
            {'filename': 'cfme-template-ext-db.yaml',
             'name': self.template_name + '-extdb'}
        ]

    @property
    def upload_folder(self):
        return self.from_template_upload('template_upload_openshift').get('upload_folder')

    @property
    def destination_directory(self):
        return os.path.join(self.upload_folder, self.template_name)

    def does_template_exist(self):
        return self.template_name in self.mgmt.list_template()

    @log_wrap('create destination directory')
    def create_destination_directory(self):
        return self.execute_ssh_command(f'mkdir -p {self.destination_directory}').success

    @log_wrap('download template')
    def download_template(self):
        return self.execute_ssh_command(
            'wget -q --no-parent --no-directories --reject "index.html*" '
            '--directory-prefix={} -r {}'.format(self.destination_directory, self.raw_image_url)
        ).success

    @log_wrap('login to openshift')
    def login_to_oc(self):
        return self.execute_ssh_command(
            'oc login --username={} --password={}'
            .format(self.creds.username, self.creds.password)
        ).success

    @log_wrap('updating tags and docker pull')
    def update_tags(self):
        result = self.execute_ssh_command(
            r'find {} -type f -name "cfme-openshift-*" -exec tail -1 {{}} \;'
            .format(self.destination_directory))

        if result.failed or not result.output:
            logger.error(f'Unable to find cfme-openshift-* files: %r')
            return False

        tags = {}
        for img_url in str(result).split():
            update_img_cmd = 'docker pull {url}'
            logger.info(f"updating image stream to tag {img_url}")
            result = self.execute_ssh_command(update_img_cmd.format(url=img_url))
            # url ex:
            # brew-pulp-docker01.web.prod.ext.phx2.redhat.com:8888/cloudforms46/cfme-openshift-httpd:2.4.6-14
            tag_name, tag_value = img_url.split('/')[-1].split(':')
            tag_url = img_url.rpartition(':')[0]
            tags[tag_name] = {'tag': tag_value, 'url': tag_url}
            if result.failed:
                logger.exception('%s: could not update image stream with url: %s',
                                 self.provider_key, img_url)
                return False
        self.tags = tags
        return True

    @log_wrap('patch template file')
    def patch_template_file(self):
        default_template_name = 'cloudforms'
        new_template_name = self.template_name
        logger.info('removing old templates from ocp if those exist')
        for template in (default_template_name, new_template_name):
            tmp_cmd = f'oc get template {template} --namespace=openshift'
            if self.execute_ssh_command(tmp_cmd).success:
                self.execute_ssh_command('oc delete template {t} '
                                '--namespace=openshift'.format(t=template))
        return True

    @log_wrap('backed name update')
    def update_name_and_create(self):
        for template in self.templates:
            cur_template = os.path.join(self.destination_directory, template['filename'])

            change_name_cmd = ("""python -c 'import yaml
data = yaml.safe_load(open("{file}"))
data["metadata"]["name"] = "{new_name}"
yaml.safe_dump(data, stream=open("{file}", "w"))'"""
                               .format(new_name=template['name'], file=cur_template))
            # our templates always have the same name but we have to keep many templates
            # of the same stream. So we have to change template name before upload to ocp
            # in addition, openshift doesn't provide any convenient way to change template name
            logger.info('Command to change name: \n%s\n', change_name_cmd)
            result = self.execute_ssh_command(change_name_cmd)
            if result.failed:
                logger.exception('%s: failed running name change command: %s',
                                 self.provider_key, result)
                return False

            logger.info("uploading main template to ocp")
            result = self.execute_ssh_command('oc create -f {t} --namespace=openshift'
                                              .format(t=cur_template))
        return result.success

    def run(self):
        if 'podtesting' not in self.provider_data.get('tags', []):
            logger.info("%s:%s No podtesting tag.", self.log_name, self.provider_key)
            return

        if '511' in self.stream or 'upstream' in self.stream:
            logger.info('Podified appliances not available for 5.11+ or upstream')
            return False

        if self.does_template_exist():
            logger.info("Template already exists.")
            return True

        if not self.create_destination_directory():
            return False

        if not self.download_template():
            return False

        if not self.login_to_oc():
            return False

        if not self.update_tags():
            return False

        if not self.update_name_and_create():
            return False

        for template in self.templates:
            result = self.track_template(
                stream=self.stream,
                provider_key=self.provider_key,
                template_name=template['name'],
                custom_data={'TAGS': self.tags}
            )
            if result is False:
                return False

        return True
