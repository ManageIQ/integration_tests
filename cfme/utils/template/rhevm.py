"""
NOT TESTED YET
"""
import re

from cfme.utils.conf import cfme_data
from cfme.utils.log import logger
from cfme.utils.template.base import log_wrap
from cfme.utils.template.base import ProviderTemplateUpload
from cfme.utils.template.base import TemplateUploadException


class RHEVMTemplateUpload(ProviderTemplateUpload):
    provider_type = 'rhevm'
    log_name = 'RHEVM'
    image_pattern = re.compile(
        r'<a href="?\'?([^"\']*(?:(?:rhevm|ovirt)[^"\']*\.(?:qcow2|qc2))[^"\'>]*)')

    @log_wrap('add glance to rhevm provider')
    def add_glance_to_provider(self):
        """Add glance as an external provider if needed"""
        glance_data = cfme_data.template_upload.get(self.glance_key)
        if self.mgmt.does_glance_server_exist(self.glance_key):
            logger.info('RHEVM provider already has glance added, skipping step')
        else:
            self.mgmt.add_glance_server(name=self.glance_key,
                                        description=self.glance_key,
                                        url=glance_data.url,
                                        requires_authentication=False)
        return True

    @log_wrap("import template from Glance server")
    def import_template_from_glance(self):
        """Import the template from glance to local rhevm datastore, sucks."""
        self.mgmt.import_glance_image(
            source_storage_domain_name=self.glance_key,
            target_cluster_name=self.provider_data.template_upload.cluster,
            source_template_name=self.image_name,
            target_template_name=self.temp_template_name,
            target_storage_domain_name=self.provider_data.template_upload.storage_domain)
        mgmt_network = self.provider_data.template_upload.get('management_network')
        rv_tmpl = self.mgmt.get_template(self.temp_template_name)
        if mgmt_network:
            # network devices, qcow template doesn't have any
            temp_nics = rv_tmpl.get_nics()
            nic_args = dict(network_name=mgmt_network, nic_name='eth0')
            if 'eth0' not in [n.name for n in temp_nics]:
                rv_tmpl.add_nic(**nic_args)
            else:
                rv_tmpl.update_nic(**nic_args)
        return True

    @log_wrap('Deploy template to vm - before templatizing')
    def deploy_vm_from_template(self):
        """Deploy a VM from the raw template with resource limits set from yaml"""
        stream_hardware = cfme_data.template_upload.hardware[self.stream]
        self.mgmt.get_template(self.temp_template_name).deploy(
            vm_name=self.temp_vm_name,
            cluster=self.provider_data.template_upload.cluster,
            storage_domain=self.provider_data.template_upload.storage_domain,
            cpu=stream_hardware.cores,
            sockets=stream_hardware.sockets,
            ram=int(stream_hardware.memory) * 2**30)  # GB -> B
        # check, if the vm is really there
        if not self.mgmt.does_vm_exist(self.temp_vm_name):
            raise TemplateUploadException('Failed to deploy VM from imported template')
        return True

    @log_wrap('Add db disk to temp vm')
    def add_disk_to_vm(self):
        """Add a disk with specs from cfme_data.template_upload
            Generally for database disk
        """
        temp_vm = self.mgmt.get_vm(self.temp_vm_name)
        if temp_vm.get_disks_count() > 1:
            logger.warning('%s Warning: found more than one disk in existing VM (%s).',
                        self.provider_key, self.temp_vm_name)
            return
        rhevm_specs = cfme_data.template_upload.template_upload_rhevm
        disk_kwargs = dict(storage_domain=self.provider_data.template_upload.storage_domain,
                           size=rhevm_specs.get('disk_size', 5000000000),
                           interface=rhevm_specs.get('disk_interface', 'virtio'),
                           format=rhevm_specs.get('disk_format', 'cow'),
                           name=rhevm_specs.get('disk_name'))
        temp_vm.add_disk(**disk_kwargs)
        # check, if there are two disks
        if temp_vm.get_disks_count() < 2:
            raise TemplateUploadException('%s disk failed to add with specs: %r',
                                          self.provider_key, disk_kwargs)
        logger.info('%s:%s Successfully added disk', self.provider_key, self.temp_vm_name)
        return True

    @log_wrap('templatize temp vm with disk')
    def templatize_vm(self):
        """Templatizes temporary VM. Result is template with two disks.
        """
        self.mgmt.get_vm(self.temp_vm_name).mark_as_template(
            template_name=self.template_name,
            cluster_name=self.provider_data.template_upload.cluster,
            storage_domain_name=self.provider_data.template_upload.get('template_domain', None),
            delete=False  # leave vm in place in case it fails, for debug
        )
        # check, if template is really there
        if not self.mgmt.does_template_exist(self.template_name):
            raise TemplateUploadException('%s templatizing %s to %s FAILED',
                                          self.provider_key, self.temp_vm_name, self.template_name)
        logger.info(":%s successfully templatized %s to %s",
                    self.provider_key, self.temp_vm_name, self.template_name)
        return True

    @log_wrap('cleanup temp resources')
    def teardown(self):
        """Cleans up all the mess that the previous functions left behind."""
        # logger.info('%s Deleting temp_vm "%s"', self.provider_key, self.temp_vm_name)
        # if self.mgmt.does_vm_exist(self.temp_vm_name):
        #    self.mgmt.get_vm(self.temp_vm_name).cleanup()

        logger.info('%s Deleting temp_template "%s"on storage domain',
                    self.provider_key, self.temp_template_name)
        if self.mgmt.does_template_exist(self.temp_template_name):
            self.mgmt.get_template(self.temp_template_name).cleanup()
        return True

    def run(self):
        """call methods for individual steps of CFME templatization of qcow2 image from glance"""
        try:
            self.glance_upload()
            self.add_glance_to_provider()
            self.import_template_from_glance()
            self.deploy_vm_from_template()
            if self.stream == 'upstream':
                self.manageiq_cleanup()
            self.add_disk_to_vm()
            self.templatize_vm()
            return True
        except Exception:
            logger.exception('template creation failed for provider {}'.format(
                self.provider_data.name))
            return False
