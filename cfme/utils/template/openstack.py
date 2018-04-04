import re

from glanceclient import Client

from cfme.utils.template.base import BaseTemplateUpload


class OpenstackTemplateUpload(BaseTemplateUpload):
    provider_type = 'openstack'
    log_name = 'RHOS'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*(?:rhos|openstack|rhelosp)[^"\'>]*)')

    def run(self):
        version = '1'
        glance = Client(version=version, session=self.mgmt.session)
        glance_image = glance.images.create(name=self.template_name,
                                            container_format='bare',
                                            disk_format='qcow2',
                                            is_public=True,
                                            copy_from=self.image_url)

        if glance_image:
            return True
