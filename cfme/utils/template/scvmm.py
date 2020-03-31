import re

from cfme.utils.template.base import log_wrap
from cfme.utils.template.base import ProviderTemplateUpload


class SCVMMTemplateUpload(ProviderTemplateUpload):
    provider_type = 'scvmm'
    log_name = 'SCVMM'
    image_pattern = re.compile(r'<a href="?\'?([^"\']*hyperv[^"\'>]*)')

    @property
    def library(self):
        return self.template_upload_data["vhds"]

    @property
    def vhd_name(self):
        return f"{self.template_name}.vhd"

    @log_wrap("upload VHD image to Library VHD folder")
    def upload_vhd(self):
        try:
            self.mgmt.download_file(self.raw_image_url, self.vhd_name, dest=self.library + "\\")
            self.mgmt.update_scvmm_library()
            return True
        except Exception:
            return False

    @log_wrap("add HW Resource File and Template to Library")
    def make_template(self):
        script = """
            $networkName = "{network}"
            $templateName = "{template_name}"
            $templateOwner = "{domain}\\{user}"
            $maxMemorySizeMb = {maxram}
            $startMemeorySizeMb = 4096
            $minMemorySizeMb = {minram}
            $cpuCount = {cores}
            $srcName = "{image}"
            $srcPath = "{vhd_path}\\$srcName"
            $dbDiskName = "{small_disk}"
            $dbDiskSrcPath = "{vhd_path}\\$dbDiskName"
            $scvmmFqdn = "{hostname}"

            $JobGroupId01 = [Guid]::NewGuid().ToString()
            $LogicalNet = Get-SCLogicalNetwork -Name $networkName
            New-SCVirtualNetworkAdapter -JobGroup $JobGroupId01 -MACAddressType Dynamic\
                -LogicalNetwork $LogicalNet -Synthetic
            New-SCVirtualSCSIAdapter -JobGroup $JobGroupId01 -AdapterID 6 -Shared $False
            New-SCHardwareProfile -Name $templateName -Owner $templateOwner -Description\
                'Temp profile used to create a VM Template' -DynamicMemoryEnabled $True\
                -DynamicMemoryMaximumMB $maxMemorySizeMb -DynamicMemoryMinimumMB $minMemorySizeMb\
                -CPUCount $cpuCount -JobGroup $JobGroupId01
            $JobGroupId02 = [Guid]::NewGuid().ToString()
            $VHD = Get-SCVirtualHardDisk -Name $srcName
            New-SCVirtualDiskDrive -IDE -Bus 0 -LUN 0 -JobGroup $JobGroupId02 -VirtualHardDisk $VHD
            $DBVHD = Get-SCVirtualHardDisk -Name $dbDiskName
            New-SCVirtualDiskDrive -IDE -Bus 1 -LUN 0 -JobGroup $JobGroupId02\
                -VirtualHardDisk $DBVHD
            $HWProfile = Get-SCHardwareProfile | where {{ $_.Name -eq $templateName }}
            New-SCVMTemplate -Name $templateName -Owner $templateOwner -HardwareProfile $HWProfile\
             -JobGroup $JobGroupId02 -RunAsynchronously -Generation 1 -NoCustomization
            Remove-HardwareProfile -HardwareProfile $templateName
        """.format(
            domain=self.mgmt.domain,
            user=self.mgmt.user,
            image=self.vhd_name,
            vhd_path=self.library,
            hostname=self.provider_data["hostname_fqdn"],
            template_name=self.template_name,
            small_disk=self.template_upload_data.get("db_disk"),
            network=self.template_upload_data.get("network"),
            minram=self.template_upload_data.get("minram"),
            maxram=self.template_upload_data.get("maxram"),
            cores=self.template_upload_data.get("cores")
        )

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
