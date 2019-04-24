import re

from cfme.utils.log import logger
from cfme.utils.template.base import log_wrap
from cfme.utils.template.base import ProviderTemplateUpload


class OpenstackTemplateUpload(ProviderTemplateUpload):
    provider_type = 'openstack'
    log_name = 'RHOS'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*(?:rhos|openstack|rhelosp)[^"\'>]*)')

    @log_wrap('Deploy template to vm - before templatizing')
    def deploy_vm_from_template(self):
        """Deploy a instance from the raw template"""
        self.mgmt.get_template(self.image_name).deploy(
            vm_name=self.temp_vm_name,
            flavor_name=self.provider_data.sprout.flavor_name,
            network_name=self.provider_data.sprout.network_name,
            floating_ip_pool=self.provider_data.sprout.floating_ip_pool,
            timeout=1800)  # rhos12 is taking a long time to provision a VM, even from local storage
        return self._vm_mgmt.exists and self._vm_mgmt.is_running

    @log_wrap("templatize VM")
    def templatize_vm(self):
        """Templatizes temporary VM"""
        try:
            self._vm_mgmt.mark_as_template(template_name=self.template_name)
            return True
        except Exception:
            return False

    @log_wrap('cleanup temp resources')
    def teardown(self):
        """Cleans up the raw template and temp VM that was templatized."""
        logger.info('%s Deleting temp_vm "%s"', self.provider_key, self.template_name)
        if self.mgmt.does_vm_exist(self.template_name):
            self.mgmt.get_vm(self.template_name).cleanup()

        logger.info('%s Deleting temp_template "%s"on storage domain',
                    self.provider_key, self.image_name)
        if self.mgmt.does_template_exist(self.image_name):
            self.mgmt.get_template(self.image_name).cleanup()
        return True

    @log_wrap('Openstack run')
    def run(self):
        self.glance_upload()
        self.deploy_vm_from_template()
        if self.stream == 'upstream':
            self.manageiq_cleanup()
        self.templatize_vm()
        return True
