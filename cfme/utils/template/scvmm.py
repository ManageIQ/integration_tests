import re

from cfme.utils.log import logger
from cfme.utils.template.base import BaseTemplateUpload


class SCVMMTemplateUpload(BaseTemplateUpload):
    provider_type = 'scvmm'
    log_name = 'SCVMM'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*hyperv[^"\'>]*)')

    @property
    def library(self):
        return self.template_upload_data.get('vhds', None)

    @property
    def vhd_name(self):
        return "{}.vhd".format(self.template_name)

    def upload_vhd(self):
        script = """
            (New-Object System.Net.WebClient).DownloadFile("{}", "{}{}")
        """.format(self.image_url, self.library, self.vhd_name)

        self.mgmt.run_script(script)
        self.mgmt.update_scvmm_library()

    def make_template(self):
        script = """
            $JobGroupId01 = [Guid]::NewGuid().ToString()
            $LogNet = Get-SCLogicalNetwork -Name \"{network}\"
            New-SCVirtualNetworkAdapter -JobGroup $JobGroupID01 -MACAddressType Dynamic `
                -LogicalNetwork $LogNet -Synthetic
            New-SCVirtualSCSIAdapter -JobGroup $JobGroupID01 -AdapterID 6 -Shared $False
            New-SCHardwareProfile -Name \"{name}\" -Owner \"{username_scvmm}\" `
                -Description 'Temp profile used to create a VM Template' -MemoryMB {ram} `
                -CPUCount {cores} -JobGroup $JobGroupID01
            $JobGroupId02 = [Guid]::NewGuid().ToString()
            $VHD = Get-SCVirtualHardDisk | where {{ $_.Location -eq \"{src_path}\" }} | `
                where {{ $_.HostName -eq \"{host_fqdn}\" }}
            New-SCVirtualDiskDrive -IDE -Bus 0 -LUN 0 -JobGroup $JobGroupID02 -VirtualHardDisk $VHD
            $HWProfile = Get-SCHardwareProfile | where {{ $_.Name -eq \"{name}\" }}
            $OS = Get-SCOperatingSystem | where {{ $_.Name -eq \"{os_type}\" }}
            New-SCVMTemplate -Name \"{name}\" -Owner \"{username_scvmm}\" `
                -HardwareProfile $HWProfile -JobGroup $JobGroupID02 -RunAsynchronously `
                -Generation 1 -NoCustomization
            Remove-HardwareProfile -HardwareProfile \"{name}\"
        """.format(
            name=self.template_name,
            network=self.template_upload_data.get('network'),
            username_scvmm="{}\\{}".format(self.mgmt.domain, self.mgmt.user),
            ram=self.template_upload_data.get('ram'),
            cores=self.template_upload_data.get('cores'),
            src_path="{}{}".format(self.library, self.vhd_name),
            host_fqdn=self.provider_data['hostname_fqdn'],
            os_type=self.template_upload_data.get('os_type')
        )
        self.mgmt.run_script(script)

    def run(self):
        logger.info("{}:{} Uploading VHD image to Library VHD folder.".format(
            self.log_name, self.provider))

        self.upload_vhd()

        logger.info("{}:{} Adding HW Resource File and Template to Library".format(
            self.log_name, self.provider))
        self.make_template()
