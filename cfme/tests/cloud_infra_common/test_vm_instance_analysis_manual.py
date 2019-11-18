import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.manual,
    pytest.mark.tier(2),
    test_requirements.smartstate,
]


def test_ssa_groups_scvmm2k12_windows2012r2_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_groups_azure_ubuntu():
    """
    1. Add Azure provider
    2. Perform SSA on Ubuntu instance.
    3. Check Groups are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_groups_scvmm2k12_centos_xfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on CentOS VM.
    Check whether Groups retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_groups_azure_rhel():
    """
    1. Add Azure provider
    2. Perform SSA on RHEL instance.
    3. Check Groups  are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_groups_scvmm2k12_rhel74():
    """
    Add SCVMM-2012 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Groups retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_groups_azure_windows2012r2_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows server 2012 R2.
    3. Check Groups are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_groups_scvmm2k16_centos_xfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on CentOS VM.
    Check whether Groups retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_groups_scvmm2k16_rhel74():
    """
    Add SCVMM-2016 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Groups retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_groups_scvmm2k16_windows2012r2_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_groups_azure_windows2016_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows2016 server.
    3. Check Groups are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_groups_ec2_rhel():
    """
    Add EC-2 provider.
    Perform SSA on RHEL instance.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_groups_ec2_ubuntu():
    """
    Add EC-2 provider.
    Perform SSA on Ubuntu instance.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_groups_ec2_windows2012r2_ntfs():
    """
    Add EC-2 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_groups_scvmm2k16_windows2016_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_groups_scvmm2k12_windows2016_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_groups_ec2_fedora():
    """
    Add EC-2 provider.
    Perform SSA on Fedora instance.
    Check whether it retrieves Groups.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_patches_azure_windows2012r2_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows server 2012 R2.
    3. Check Patches are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_patches_ec2_windows2012r2_ntfs():
    """
    Add EC-2 provider.
    Perform SSA on Windows 2012 R2 server VM.
    Check whether Patches are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_patches_azure_windows2016_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows2016 server.
    3. Check Patches are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_windows2016_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows2016 server.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.8
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k16_centos_xfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on CentOS VM.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_multiple_vms():
    """
    Perform SSA on multiple VMs.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: critical
        initialEstimate: 1/4h
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k16_windows2016_disk_fileshare():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2016 server R2 VM having disk located on
    Fileshare.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k12_windows2016_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k12_windows2016_refs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server R2 VM having ReFS filesystem.
    It should fail-->  Unable to mount filesystem. Reason:[ReFS is Not
    Supported]

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_windows2012r2_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows2012 R2 server Instance.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.8
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k16_windows2012r2_refs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2012 server R2 VM having ReFS filesystem.
    It should fail-->  Unable to mount filesystem. Reason:[ReFS is Not
    Supported]

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_ec2_customer_scenario():
    """
    This test case should be checked after each CFME release.(which
    supports EC2 SSA)
    Add EC-2 provider.
    Perform SSA on instance.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k16_schedule():
    """
    Trigger SmartState Analysis via schedule on VM.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: critical
        initialEstimate: 1/4h
        startsin: 5.3
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k12_second_disk_refs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2012 server R2 VM having
    NTFS as Primary Disk filesystem and secondary disk ReFS filesystem.
    It should pass without any error.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_ec2_fedora():
    """
    Add EC-2 provider.
    Perform SSA on Fedora instance.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_compliance_policy():
    """
    Checks compliance condition on VM/Instance which triggers Smartstate
    Analysis on VM/Instance.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: critical
        initialEstimate: 1/4h
        tags: smartstate
    """
    pass


def test_ssa_vm_vsphere6_nested_wimdows7_xfs_ssui():
    """
    1. Provision service with Windows 7 VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.8
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k12_compliance_policy():
    """
    Checks compliance condition on VM/Instance which triggers Smartstate
    Analysis on VM/Instance.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: critical
        initialEstimate: 1/4h
        startsin: 5.3
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k16_multiple_vms():
    """
    Perform SSA on multiple VMs.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: critical
        initialEstimate: 1/4h
        startsin: 5.3
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_schedule():
    """
    Trigger SmartState Analysis via schedule on VM.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: critical
        initialEstimate: 1/4h
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k16_windows2012r2_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_managed_disk():
    """
    Perform SSA on Managed disk on Azure provider.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        tags: smartstate
    """
    pass


def test_ssa_vm_ec2_windows2012_ssui():
    """
    1. Provision service with Windows 2012 VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_vm_ec2_windows2012r2_ntfs():
    """
    Add EC-2 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_rhel():
    """
    Create or Use existing RHEL VM/Instance present in Azure.
    Perform SSA on RHEL VM/Instance when
    VM/Instance is Powered ON
    VM/Instance is Powered OFF

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.6
        upstream: no
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_wimdows2016_ssui():
    """
    1. Provision service with Windows 2016 VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.8
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_windows2016_refs():
    """
    This test is to verify that you get an error when trying to perform
    SSA on a Windows2016 VM that has a ReFS formatted disk attached.  Here
    is the before and after.
    05/26/17 18:13:36 UTC
    05/26/17 18:10:56 UTC
    05/26/17 18:10:46 UTC
    finished
    Unable to mount filesystem. Reason:[ReFS is Not Supported]
    Scan from Vm ReFS16on16a
    admin
    EVM
    Scanning completed.
    05/26/17 16:12:45 UTC
    05/26/17 16:08:30 UTC
    05/26/17 16:08:26 UTC
    finished
    Process completed successfully
    Scan from Vm ReFS16on16a
    admin
    EVM
    Synchronization complete

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/4h
        setup: Need to create a windows 2016 instance and save it onto the ReFS disks
               on Azure.
               Add a second disk to the VM config.  Open VM, initialize disk and
               format it as ReFS
               Refresh you CFME appliance
               Perform SSA on that VM.
               Best to just use existing ReFS vms.
        startsin: 5.6
        upstream: yes
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k12_multiple_vms():
    """
    Perform SSA on multiple VMs.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: critical
        initialEstimate: 1/4h
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k12_centos_xfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on CentOS VM.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_region():
    """
    1. Add an Azure Instance in one region and assign it to a Resource
    Group from another region.

    Bugzilla:
        1503295

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k16_windows2016_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k16_windows2016_refs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2016 server R2 VM having ReFS filesystem.
    It should fail-->  Unable to mount filesystem. Reason:[ReFS is Not
    Supported]

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_ec2_ubuntu_ssui():
    """
    1. Provision service with Ubuntu VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_wimdows2012_ssui():
    """
    1. Provision service with Windows 2012 VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.8
        tags: smartstate
    """
    pass


def test_ssa_vm_ec2_rhel():
    """
    Add EC-2 provider.
    Perform SSA on RHEL instance.
    Cross-check whether smartstate instance created from AMI mentioned in
    production.yml.

    Bugzilla:
        1547228

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_vm_ec2_agent_tracker():
    """
    Bugzilla:
        1557452

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_windows2012r2_refs():
    """
    This test is to verify that you get an error when trying to perform
    SSA on a Windows2012 r2 instance that has a ReFS formatted disk
    attached.  Here is the before and after.
    05/26/17 18:13:36 UTC
    05/26/17 18:10:56 UTC
    05/26/17 18:10:46 UTC
    finished
    Unable to mount filesystem. Reason:[ReFS is Not Supported]
    Scan from Vm ReFS16on16a
    admin
    EVM
    Scanning completed.
    05/26/17 16:12:45 UTC
    05/26/17 16:08:30 UTC
    05/26/17 16:08:26 UTC
    finished
    Process completed successfully
    Scan from Vm ReFS16on16a
    admin
    EVM
    Synchronization complete

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseposneg: negative
        initialEstimate: 1/2h
        setup: Need to create a windows 2012r2 instance and save it onto the ReFS
               disks on Azure.
               Add a second disk to the VM config.  Open VM, initialize disk and
               format it as ReFS
               Refresh you CFME appliance
               Perform SSA on that VM.
               Best to just use existing ReFS vms.
        startsin: 5.8
        tags: smartstate
    """
    pass


def test_ssa_vm_ec2_ubuntu():
    """
    Add EC-2 provider.
    Perform SSA on Ubuntu instance.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_vm_vsphere6_nested_centos_xfs_ssui():
    """
    1. Provision service with CentOS VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.8
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_ubuntu():
    """
    Perform SSA on Ubuntu VM

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k12_windows2012r2_refs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2012 server R2 VM having ReFS filesystem.
    It should fail-->  Unable to mount filesystem. Reason:[ReFS is Not
    Supported]

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k12_windows2012r2_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_non_managed_disk():
    """
    Perform SSA on non-managed (blod) disk on Azure provider.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k12_windows2016_disk_fileshare():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server R2 VM having disk located on
    Fileshare..

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k16_rhel74():
    """
    Add SCVMM-2016 provider.
    Perform SSA on RHEL 7.4 VM.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_azure_ubuntu_ssui():
    """
    1. Provision service with Ubuntu VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.8
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k16_second_disk_refs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server R2 VM having
    NTFS as Primary Disk filesystem and secondary disk ReFS filesystem.
    It should pass without any error.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k12_schedule():
    """
    Trigger SmartState Analysis via schedule on VM.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: critical
        initialEstimate: 1/4h
        tags: smartstate
    """
    pass


def test_ssa_vm_ec2_windows2016_ssui():
    """
    1. Provision service with Windows 2016 VM
    2. Perform SSA on it.
    3. Check data populated on Provisioned Service in SSUI Dashboard.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_vm_disk_usage():
    """
    1. Add a VMware provider
    2. Run SSA for the VM and the data store (might not be necessary, but
    wanted to make sure all data collection is executed)
    3. Navigate to a VM
    4. Click on "number of disks"

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.3
        tags: smartstate
    """
    pass


def test_ssa_vm_cancel_task():
    """
    Start SSA on VM and wait snapshot to create.
    Cancel the task immediately.
    Bugzilla:
        1538347

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k12_rhel74():
    """
    Add SCVMM-2012 provider.
    Perform SSA on RHEL 7.4 VM.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_scvmm2k16_compliance_policy():
    """
    Checks compliance condition on VM/Instance which triggers Smartstate
    Analysis on VM/Instance.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: critical
        initialEstimate: 1/4h
        startsin: 5.3
        tags: smartstate
    """
    pass


def test_ssa_vm_azure():
    """
    Perform SSA on Instance on States:
    1. Power ON
    2. Power OFF.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_ec2_vpc():
    """
    1. Create a VPC;
    2. Do not attach any gateway to it;
    3. Turn on "DNS resolution", "DNS hostname" to "yes";
    4. Deploy an agent on this VPC;
    5. Run SSA job;

    Bugzilla:
        1557377

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_users_azure_windows2016_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows2016 server.
    3. Check Users are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_users_azure_rhel():
    """
    1. Add Azure provider
    2. Perform SSA on RHEL instance.
    3. Check Users  are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_users_scvmm2k16_centos_xfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on CentOS VM.
    Check whether Users retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_users_scvmm2k12_windows2016_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_users_scvmm2k16_windows2016_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_users_scvmm2k12_centos_xfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on CentOS VM.
    Check whether Users retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_users_ec2_ubuntu():
    """
    Add EC-2 provider.
    Perform SSA on Ubuntu instance.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_users_scvmm2k12_rhel74():
    """
    Add SCVMM-2012 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Users retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_users_azure_ubuntu():
    """
    1. Add Azure provider
    2. Perform SSA on Ubuntu Instance.
    3. Check Users are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_users_ec2_fedora():
    """
    Add EC-2 provider.
    Perform SSA on Fedora instance.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_users_scvmm2k16_rhel74():
    """
    Add SCVMM-2016 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Users retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_users_scvmm2k16_windows2012r2_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_users_scvmm2k12_windows2012r2_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_users_ec2_rhel():
    """
    Add EC-2 provider.
    Perform SSA on RHEL instance.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_users_azure_windows2012r2_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows server 2012 R2.
    3. Check Users are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_users_ec2_windows2012r2_ntfs():
    """
    Add EC-2 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Users.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_packages_ec2_ubuntu():
    """
    Add EC-2 provider.
    Perform SSA on Ubuntu instance.
    Check whether it retrieves Packages.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_packages_scvmm2k12_rhel74():
    """
    Add SCVMM-2012 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Packages retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_packages_ec2_fedora():
    """
    Add EC-2 provider.
    Perform SSA on Fedora instance.
    Check whether it retrieves Packages.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_packages_scvmm2k16_centos_xfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on CentOS VM.
    Check whether Packages retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_packages_ec2_rhel():
    """
    Add EC-2 provider.
    Perform SSA on RHEL instance.
    Check whether it retrieves Packages.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_packages_scvmm2k12_windows2016_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Applications.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_packages_azure_ubuntu():
    """
    1. Add Azure provider
    2. Perform SSA on Ubuntu Instance.
    3. Check Packages are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_packages_azure_windows2016_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows2016 server.
    3. Check Applications are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_packages_scvmm2k12_windows2012r2_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Applications.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_packages_scvmm2k16_rhel74():
    """
    Add SCVMM-2016 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Packages retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_packages_scvmm2k16_windows2012r2_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Applications.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_packages_ec2_windows2012r2_ntfs():
    """
    Add EC-2 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Applications.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_packages_scvmm2k16_windows2016_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Applications.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_packages_azure_rhel():
    """
    1. Add Azure provider
    2. Perform SSA on RHEL instance.
    3. Check Packages are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_packages_azure_windows2012r2_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows server 2012 R2.
    3. Check Packages are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_packages_scvmm2k12_centos_xfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on CentOS VM.
    Check whether Packages retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_with_snapshot_scvmm2():
    """
    Needed to verify this bug -
    https://bugzilla.redhat.com/show_bug.cgi?id=1376172
    There is a vm called LocalSSATest33 that is preconfigured for this
    test.
    I"ll do these one off tests for a while.

    Bugzilla:
        1376172

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.6.1
        upstream: yes
        tags: smartstate
    """
    pass


def test_ssa_host_os_info():
    """
    Checks the host's OS name and version

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: medium
        initialEstimate: 1/2h
        tags: smartstate
    """
    pass


def test_ssa_files_scvmm2k12_centos_xfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on CentOS VM.
    Check whether Files retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_files_azure_windows2016_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows2016 server.
    3. Check Files are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_files_scvmm2k12_windows2016_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_files_azure_ubuntu():
    """
    1. Add Azure provider
    2. Perform SSA on Ubuntu instance.
    3. Check Files are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_files_ec2_rhel():
    """
    Add EC-2 provider.
    Perform SSA on RHEL instance.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_files_ec2_fedora():
    """
    Add EC-2 provider.
    Perform SSA on Fedora instance.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_files_scvmm2k12_rhel74():
    """
    Add SCVMM-2012 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Files retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_files_scvmm2k16_centos_xfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on CentOS VM.
    Check whether Files retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_files_scvmm2k16_rhel74():
    """
    Add SCVMM-2016 provider.
    Perform SSA on RHEL 7.4 VM.
    Check whether Files retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_files_scvmm2k16_windows2012r2_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_files_scvmm2k12_windows2012r2_ntfs():
    """
    Add SCVMM-2012 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_files_ec2_ubuntu():
    """
    Add EC-2 provider.
    Perform SSA on Ubuntu instance.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_files_scvmm2k16_windows2016_ntfs():
    """
    Add SCVMM-2016 provider.
    Perform SSA on Windows 2016 server VM having NTFS filesystem.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_files_azure_windows2012r2_ntfs():
    """
    1. Add Azure provider
    2. Perform SSA on Windows server 2012 R2.
    3. Check Files are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_files_ec2_windows2012r2_ntfs():
    """
    Add EC-2 provider.
    Perform SSA on Windows 2012 server R2 VM having NTFS filesystem.
    Check whether it retrieves Files.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        startsin: 5.9
        tags: smartstate
    """
    pass


def test_ssa_files_azure_rhel():
    """
    1. Add Azure provider
    2. Perform SSA on RHEL instance.
    3. Check Files are retrieved.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.6
        tags: smartstate
    """
    pass


def test_ssa_vm_files_unicode():
    """
    Make sure https://bugzilla.redhat.com/show_bug.cgi?id=1221149 is fixed

    Bugzilla:
        1221149

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/2h
        tags: smartstate
    """
    pass


def test_ssa_files_windows_utf_8_files():
    r"""
    Configure SSA to include c:\windows\debug\* and verify its content

    Polarion:
        assignee: sbulage
        caseimportance: medium
        casecomponent: SmartState
        initialEstimate: 1/2h
        setup: 1. Configure SSA profile to include c:\windows\debug\*
               2. Run SSA
               3. View the content of all the files (i.e., mrt.log, passwd.log,
               sammui.log, wlms.log, etc...)
        startsin: 5.3
        tags: smartstate
    """
    pass


@test_requirements.drift
def test_drift_analysis_vpshere6_rhel():
    """
    1. Go to Compute-> Infrastructure-> Virtual Machines -> Select any vm
    for SSA
    2. Perform SSA on VM
    3. Next, Reconfigure the VM with change in memory and CPU etc.
    4. Again perform SSA on VM
    5. Next, compare drift history
    6. Check the drift comparison
    Validate that updated values get displayed.

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.3
        tags: smartstate
    """
    pass


@pytest.mark.meta(coverage=[1646467])
def test_provider_refresh_after_ssa():
    """
    Verify that system info obtained by ssa isn't wiped out after provider refresh

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        tags: smartstate
        testSteps:
            1. Add a Provider.
            2. provision vm or take one of its images
            3. run ssa on that vm or image
            4. kick off provider refresh
        expectedResults:
            1.
            2.
            3. system os and etc is fulfilled for that vm/image
            4. vm/system info hasn't been wiped out by provider refresh
    """
