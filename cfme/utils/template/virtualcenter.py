from cached_property import cached_property
import re

from cfme.utils.log import logger
from cfme.utils.template.base import ProviderTemplateUpload, log_wrap

NUM_OF_TRIES = 5


class VMWareTemplateUpload(ProviderTemplateUpload):
    provider_type = 'virtualcenter'
    log_name = 'VSPHERE'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*vsphere[^"\'>]*)')

    @log_wrap("upload template")
    def upload_template(self):
        cmd_args = [
            "ovftool --noSSLVerify",
            # prefer the datastore from template_upload
            "--datastore={}".format(self.provider_data.provisioning.datastore),  # move later
            "--name={}".format(self.temp_template_name),
            "--vCloudTemplate=True",
            "--overwrite",
            self.raw_image_url,
            "'vi://{}:{}@{}/{}/host/{}/'".format(self.mgmt.username,
                                                 self.mgmt.password,
                                                 self.mgmt.hostname,
                                                 self.template_upload_data.datacenter,
                                                 self.template_upload_data.cluster)
        ]

        if 'proxy' in self.template_upload_data.keys():
            cmd_args.append("--proxy={}".format(self.template_upload_data.proxy))

        command = ' '.join(cmd_args)

        for i in range(0, 1):
            # run command against the tool client machine
            upload_result = self.execute_ssh_command(command, client_args=self.tool_client_args)
            if upload_result.success:
                return True
            else:
                logger.warning('Retrying template upload via ovftool')

    @cached_property
    def _vm_mgmt(self):
        return self.mgmt.get_vm(self.template_name)

    @cached_property
    def _temp_vm_mgmt(self):
        return self.mgmt.get_vm(self.temp_template_name)

    @log_wrap("add disk to VM")
    def add_disk_to_vm(self):
        # adding disk #1 (base disk is 0)
        result, msg = self._temp_vm_mgmt.add_disk(
            capacity_in_kb=self.template_upload_data.disk_size,
            provision_type='thin')
        return result

    @log_wrap("templatize VM")
    def templatize_vm(self):
        # move it to other datastore
        host = self.template_upload_data.get('host') or self.mgmt.list_host().pop()
        self._temp_vm_mgmt.clone(vm_name=self.template_name,
                                 datastore=self.template_upload_data.template_datastore,
                                 host=host,
                                 relocate=True)
        assert self._vm_mgmt.exists
        try:
            self._vm_mgmt.mark_as_template()
            return True
        except Exception:
            return False

    def run(self):
        template_upload_vsphere = self.from_template_upload('template_upload_vsphere')

        if template_upload_vsphere.get('upload'):
            if not self.upload_template():
                return False

        if template_upload_vsphere.get('disk'):
            if not self.add_disk_to_vm():
                return False

        if template_upload_vsphere.get('template'):
            if not self.templatize_vm():
                return False

        return True
