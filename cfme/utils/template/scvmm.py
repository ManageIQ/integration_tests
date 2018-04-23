import re

from cfme.utils.template.base import ProviderTemplateUpload, log_wrap


class SCVMMTemplateUpload(ProviderTemplateUpload):
    provider_type = 'scvmm'
    log_name = 'SCVMM'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*hyperv[^"\'>]*)')

    @property
    def library(self):
        return self.template_upload_data.get('vhds', None)

    @property
    def vhd_name(self):
        return "{}.vhd".format(self.template_name)

    @log_wrap("upload VHD image to Library VHD folder")
    def upload_vhd(self):
        script = """
                    (New-Object System.Net.WebClient).DownloadFile("{}", "{}{}")
                """.format(self.raw_image_url, self.library, self.vhd_name)

        try:
            self.mgmt.run_script(script)
            self.mgmt.update_scvmm_library()
            return True

        except Exception:
            return False

    @log_wrap("add HW Resource File and Template to Library")
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
        """.format(name=self.template_name,
                   network=self.template_upload_data.get('network'),
                   username_scvmm="{}\\{}".format(self.mgmt.domain, self.mgmt.user),
                   ram=self.template_upload_data.get('ram'),
                   cores=self.template_upload_data.get('cores'),
                   src_path="{}{}".format(self.library, self.vhd_name),
                   host_fqdn=self.provider_data['hostname_fqdn'],
                   os_type=self.template_upload_data.get('os_type'))

        try:
            self.mgmt.run_script(script)
            return True

        except Exception:
            return False

    def run(self):
        template_upload_scvmm = self.from_template_upload('template_upload_scvmm')

        if template_upload_scvmm.get('disk'):
            if not self.upload_vhd():
                return False

        if template_upload_scvmm.get('template'):
            if not self.make_template():
                return False

        return True
