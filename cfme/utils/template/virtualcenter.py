from cached_property import cached_property
import re

from cfme.utils.template.base import ProviderTemplateUpload, log_wrap

NUM_OF_TRIES = 5


class VMWareTemplateUpload(ProviderTemplateUpload):
    provider_type = 'virtualcenter'
    log_name = 'VSPHERE'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*vsphere[^"\'>]*)')

    def get_creds(self, creds_type=None, **kwargs):
        host_default = self.from_credentials('host_default')
        hostname = self.from_template_upload('template_upload_vsphere').get('ovf_tool_client')

        creds = {
            'hostname': hostname,
            'username': host_default['username'],
            'password': host_default['password']
        }

        return creds

    @log_wrap("upload template")
    def upload_template(self):
        cmd_args = [
            "ovftool --noSSLVerify",
            "--datastore={}".format(self.provider_data.provisioning.datastore),
            "--name={}".format(self.template_name),
            "--vCloudTemplate=True",
            "--overwrite",
            self.image_url,
            "'vi://{}:{}@{}/{}/host/{}'".format(self.mgmt.username,
                                                self.mgmt.password,
                                                self.mgmt.hostname,
                                                self.template_upload_data.datacenter,
                                                self.template_upload_data.cluster)
        ]

        if 'proxy' in self.template_upload_data.keys():
            cmd_args.append("--proxy={}".format(self.template_upload_data.proxy))

        command = ' '.join(cmd_args)

        for i in range(0, NUM_OF_TRIES):
            upload_result = self.execute_ssh_command(command)
            if upload_result.success:
                return True

    @cached_property
    def _vm_mgmt(self):
        return self.mgmt.get_vm(self.template_name)

    @log_wrap("add disk to VM")
    def add_disk_to_vm(self):
        # adding disk #1 (base disk is 0)
        result, msg = self._vm_mgmt.add_disk(capacity_in_kb=8388608,
                                             provision_type='thin')

        if result[0]:
            return True

    @log_wrap("templatize VM")
    def templatize_vm(self):
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
