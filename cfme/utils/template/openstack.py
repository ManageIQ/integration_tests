import re

from fauxfactory import gen_alphanumeric
from glanceclient import Client

from cfme.utils.wait import wait_for
from cfme.utils.template.base import ProviderTemplateUpload, log_wrap


class OpenstackTemplateUpload(ProviderTemplateUpload):
    provider_type = 'openstack'
    log_name = 'RHOS'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*(?:rhos|openstack|rhelosp)[^"\'>]*)')

    @log_wrap("upload template to glance")
    def upload_template(self):
        version = '1'

        glance = Client(version=version, session=self.mgmt.session)
        glance_image = glance.images.create(name=self.template_name,
                                            container_format='bare',
                                            disk_format='qcow2',
                                            is_public=True,
                                            copy_from=self.image_url)

        wait_for(lambda: glance_image.manager.get(glance_image).status == 'active',
                 fail_condition=False,
                 delay=5,
                 logger=None)

        return True

    @log_wrap('deploy template')
    def deploy_template(self):
        deploy_args = {
            'provider': self.provider,
            'vm_name': 'test_{}_{}'.format(self.template_name, gen_alphanumeric(8)),
            'template': self.template_name,
            'deploy': True,
            'network_name': self.provider_data.get('network', 'default')}

        self.mgmt.deploy_template(**deploy_args)
        return True

    def run(self):
        self.upload_template()
        self.deploy_template()

        return True
