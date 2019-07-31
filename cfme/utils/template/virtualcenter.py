import re

from cached_property import cached_property

from cfme.utils.log import logger
from cfme.utils.template.base import log_wrap
from cfme.utils.template.base import ProviderTemplateUpload

NUM_OF_TRIES = 5


class VMWareTemplateUpload(ProviderTemplateUpload):
    provider_type = 'virtualcenter'
    log_name = 'VSPHERE'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*vsphere[^"\'>]*)')

    @cached_property
    def _temp_vm_mgmt(self):
        return self.mgmt.get_vm(self.temp_template_name)

    @cached_property
    def _picked_datastore(self):
        # Priority goes to template_datastore_cluster
        return (self.template_upload_data.get('template_datastore_cluster') or
                self.template_upload_data.get('template_datastore') or
                self.template_upload_data.get('allowed_datastores'))

    @log_wrap("upload template")
    def upload_template(self):
        cmd_args = [
            "ovftool --noSSLVerify",
            "--datastore={}".format(self._picked_datastore),
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

        if 'proxy' in list(self.template_upload_data.keys()):
            cmd_args.append("--proxy={}".format(self.template_upload_data.proxy))

        command = ' '.join(cmd_args)

        for i in range(0, 1):
            # run command against the tool client machine
            upload_result = self.execute_ssh_command(command, client_args=self.tool_client_args)
            if upload_result.success:
                return True
            else:
                logger.error('Failure running ovftool: %s', upload_result.output)
                logger.warning('Retrying template upload via ovftool')

    @log_wrap("add disk to VM")
    def add_disk_to_vm(self):
        # adding disk #1 (base disk is 0)
        result, msg = self._temp_vm_mgmt.add_disk(
            capacity_in_kb=self.template_upload_data.disk_size,
            provision_type='thin')
        return result

    @log_wrap("deploy VM")
    def deploy_vm(self):
        # Move the VM to the template datastore and set the correct name
        host = self.template_upload_data.get('host') or self.mgmt.list_host().pop()
        self._temp_vm_mgmt.clone(vm_name=self.temp_vm_name,
                                 datastore=self._picked_datastore,
                                 host=host,
                                 relocate=True)
        # For Upstream builds, the VM needs to be on to perform cleanup from
        # appliance-initialization
        if self.stream == 'upstream' and self._vm_mgmt.exists:
            self._temp_vm_mgmt.start()
        return self._vm_mgmt.exists

    @log_wrap("templatize VM")
    def templatize_vm(self):
        try:
            self._vm_mgmt.mark_as_template(template_name=self.template_name)
            return True
        except Exception:
            return False

    def run(self):
        template_upload_vsphere = self.from_template_upload('template_upload_vsphere')
        try:
            if template_upload_vsphere.get('upload'):
                self.upload_template()
            if template_upload_vsphere.get('disk'):
                self.add_disk_to_vm()
            if template_upload_vsphere.get('template'):
                self.deploy_vm()
                # Cleanup from appliance-initialization if upstream
                if self.stream == 'upstream':
                    self.manageiq_cleanup()
                self.templatize_vm()
            return True
        except Exception:
            logger.exception('template creation failed for provider {}'.format(
                self.provider_data.name))
            return False
