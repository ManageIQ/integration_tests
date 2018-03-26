import re
from cfme.utils.log import logger
from cfme.utils.template.base import BaseTemplateUpload
from cfme.utils.template.exc import TemplateUploadException
from cfme.utils.conf import cfme_data, credentials


NUM_OF_TRIES = 5
TEMPLATE_UPLOAD_VSPHERE = cfme_data.template_upload.template_upload_vsphere


class VirtualCenterTemplateUpload(BaseTemplateUpload):
    provider_type = 'virtualcenter'
    log_name = 'VSPHERE'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*vsphere[^"\'>]*)')

    def get_creds(self, creds_type=None, **kwargs):
        creds = {
            'hostname': TEMPLATE_UPLOAD_VSPHERE['ovf_tool_client'],
            'username': credentials.host_default['username'],
            'password': credentials.host_default['password']
        }
        return creds

    def upload_template(self):
        template_upload = self.provider_data.template_upload
        cmd_args = [
            "ovftool --noSSLVerify",
            "--datastore={}".format(self.provider_data.provisioning.datastore),
            "--name={}".format(self.template_name),
            "--vCloudTemplate=True",
            "--overwrite",
            self.image_url,
            "'vi://{}:{}@{}/{}/host/{}'".format(self.mgmt.username, self.mgmt.password,
                                                self.mgmt.hostname, template_upload.datacenter,
                                                template_upload.cluster)
        ]

        if 'proxy' in template_upload.keys():
            cmd_args.append("--proxy={}".format(template_upload.proxy))

        command = ' '.join(cmd_args)

        for i in range(0, NUM_OF_TRIES):
            upload_result = self.execute_ssh_command(command)
            if upload_result.success:
                logger.info("%s:%s Successfully uploaded template: %s",
                            self.log_name, self.provider, self.template_name)
                return True

        raise TemplateUploadException("Exception during uploading template.")

    def add_disk_to_vm(self):
        # adding disk #1 (base disk is 0)
        result, msg = self.mgmt.add_disk_to_vm(vm_name=self.template_name,
                                               capacity_in_kb=8388608,
                                               provision_type='thin')

        if result[0]:
            logger.info("%s:%s Added disk to VM %s",
                        self.log_name, self.provider, self.template_name)
        else:
            logger.error("%s:%s Failed to add disk to VM".format(
                self.log_name, self.provider))
            raise TemplateUploadException("Exception during upload_template.")

    def templatize_vm(self):
        try:
            self.mgmt.mark_as_template(self.template_name)
            logger.info("%s:%s Successfully templatized %s",
                        self.log_name, self.provider, self.template_name)
        except Exception:
            logger.error("%s:%s Failed to templatize %s",
                         self.log_name, self.provider, self.template_name)
            raise TemplateUploadException("Templatizing failed.")

    def run(self):
        results = []

        if TEMPLATE_UPLOAD_VSPHERE['upload']:
            upload = self.upload_template()
            results.append(upload)

        if TEMPLATE_UPLOAD_VSPHERE['disk']:
            disk = self.add_disk_to_vm()
            results.append(disk)

        if TEMPLATE_UPLOAD_VSPHERE['template']:
            template = self.templatize_vm()
            results.append(template)

        return all(results)
