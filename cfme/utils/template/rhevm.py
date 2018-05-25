"""
NOT TESTED YET
"""

import re
from fauxfactory import gen_alphanumeric
from glanceclient import Client
from keystoneauth1 import session, loading
try:
    from ovirtsdk.xml import params
except ImportError:
    pass

from cfme.utils.conf import cfme_data, credentials
from cfme.utils.log import logger
from cfme.utils.template.base import ProviderTemplateUpload, log_wrap


class RHEVMTemplateUpload(ProviderTemplateUpload):
    provider_type = 'rhevm'
    log_name = 'RHEVM'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*(?:\.qcow2)[^"\'>]*)')
    glance_server = 'glance11-server'

    @property
    def temp_template_name(self):
        return 'auto-tmp-{}-{}'.format(gen_alphanumeric(8), self.template_name)

    @property
    def temp_vm_name(self):
        return 'auto-vm-{}-{}'.format(gen_alphanumeric(8), self.template_name)

    @log_wrap("download template")
    def download_template(self):
        command = 'curl -O {}'.format(self.image_url)
        if self.execute_ssh_command(command, timeout=1800).success:
            return True

    @log_wrap("upload template to glance")
    def upload_to_glance(self):
        api_version = '2'
        glance_data = cfme_data['template_upload'][self.glance_server]
        creds_key = glance_data['credentials']
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(
            auth_url=glance_data['auth_url'],
            username=credentials[creds_key]['username'],
            password=credentials[creds_key]['password'],
            tenant_name=credentials[creds_key]['tenant'])
        glance_session = session.Session(auth=auth)
        glance = Client(version=api_version, session=glance_session)

        for img in glance.images.list():
            if img.name == self.template_name:
                logger.info("(template-upload) [%s:%s:%s] Template already exists on Glance.",
                            self.log_name, self.provider, self.template_name)
                return True

        glance_image = glance.images.create(name=self.template_name,
                                            container_format='bare',
                                            disk_format='qcow2',
                                            visibility="public")
        glance.images.add_location(glance_image.id, self.image_url, {})
        if glance_image:
            logger.info("{}:{} Successfully uploaded template: {}".format(
                self.log_name, self.provider, self.template_name))
            return True

    @log_wrap("import template from Glance server")
    def import_template_from_glance(self):
        try:
            if self.mgmt.api.templates.get(self.temp_template_name):
                return
            sd = self.mgmt.api.storagedomains.get(name=self.glance_server)
            actual_template = sd.images.get(name=self.template_name)

            actual_storage_domain = self.mgmt.api.storagedomains.get(
                self.provider_data['template_upload']['sdomain'])

            actual_cluster = self.mgmt.api.clusters.get(
                self.provider_data['template_upload']['cluster'])

            import_action = params.Action(async=True, cluster=actual_cluster,
                                          storage_domain=actual_storage_domain)
            actual_template.import_image(action=import_action)

            if self.mgmt.api.templates.get(self.temp_template_name):
                return True

        except:
            return False

    def run(self):
        self.upload_to_glance()
        self.import_template_from_glance()
