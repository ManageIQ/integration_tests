import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.manual,
    pytest.mark.tier(2),
    test_requirements.smartstate,
]


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


def test_ssa_vm_vsphere6_nested_windows7_xfs_ssui():
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
