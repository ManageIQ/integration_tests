import re

from cfme.utils.template.base import ProviderTemplateUpload, log_wrap


class OpenstackTemplateUpload(ProviderTemplateUpload):
    provider_type = "openstack"
    log_name = "RHOS"
    image_pattern = re.compile(r'<a href="?\'?([^"\']*(?:rhos|openstack|rhelosp)[^"\'>]*)')

    @log_wrap("Openstack run")
    def run(self):
        self.glance_upload()
        return True
