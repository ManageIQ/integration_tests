import re

from glanceclient import Client

from cfme.utils.log import logger
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

        if not glance_image:
            logger.exception("%s:%s Error while uploading template: %s",
                             self.log_name, self.provider, self.template_name)
            return False

        return True
