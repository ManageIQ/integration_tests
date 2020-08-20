import pytest

from cfme import test_requirements

pytestmark = [
    test_requirements.provision
]


@pytest.mark.manual
@pytest.mark.tier(2)
def test_provision_bad_password():
    """
    This test verifies that an acceptable password is entered when
    provisioning an Azure VM from an Azure image.  "test" won"t work.

    Polarion:
        assignee: jhenner
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_provision_request_approved_msg():
    """
    Test the flash message content on denial; should contain "approved"

    Polarion:
        assignee: jhenner
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_none_public_ip_provision_azure():
    """
    Testing provision w/o public IP - to cover -

    Bugzilla:
        1497202

    1.Provision VM
    2.Verify we don"t have public IP

    Polarion:
        assignee: jhenner
        casecomponent: Provisioning
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
        startsin: 5.9
        tags: provision
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
@test_requirements.azure
def test_public_ip_reuse_azure():
    """
    Testing Public Ip reuse
    prerequirements:
    Free Public IP associated with Network interface but not assigned to
    any VM
    Select PubIP on Environment tab during provisioning

    Polarion:
        assignee: anikifor
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.7
        tags: provision
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_vmware_default_placement_vmware():
    """
    Test host autoplacement provisioning on VMware. now we are able to get
    DRS property of the Cluster from VC and specify if selected Cluster
    requires pre-selected Host Name or not
    CFME: Cluster properties -  DRS = True
    VC: Cluster / Manage / Settings / vSphere DRS

    Polarion:
        assignee: jhenner
        casecomponent: Provisioning
        initialEstimate: 1/6h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_provision_with_storage_profile_vsphere():
    """
    Starting from vc 55 we may use Storage Profiles(Policies) in CFME
    Prerequisite - VC with configured Storage Policies/VM with assigned
    St.Policy

    Polarion:
        assignee: jhenner
        casecomponent: Provisioning
        initialEstimate: 1/6h
        startsin: 5.7
        tags: provision, vmware
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_vm_placement_with_duplicated_folder_name_vmware():
    """
    This testcase is related to -

    Bugzilla:
        1414136

    Description of problem:
    Duplicate folder names between host & vm/templates causes placement
    issues
    Hosts & Clusters shared a common folder name with a folder that also
    resides in vm & templates inside of VMWare which will cause CloudForms
    to attempt to place a vm inside of the Host & Clusters folder.

    Polarion:
        assignee: jhenner
        casecomponent: Provisioning
        caseimportance: low
        initialEstimate: 1/4h
        startsin: 5.7
        testtype: nonfunctional
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_multiple_vm_provision_with_public_ip_azure():
    """
    Bugzilla:
        1531275

    Wait for BZ to get resolved first. Design solution still wasn"t made
    "This isn"t a dup of the other ticket, as the distinction is single vs
    multiple VM"s. So, what we need to do is alter the UI to allow two
    options when provisioning multiple VM"s - public or private."
    1.Provision multiple VMs w/ or w/o Public IP
    Currently we are not able to select any Public IP option when we
    provision multiple VMs - all VMs will get new Public IP

    Polarion:
        assignee: jhenner
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_provision_request_info():
    """
    1)Create provisioning request
    2)Open Request info
    3)Check if Request Info is filled (mainly Environment tab etc)
    all - preselected options should be mentioned here

    Polarion:
        assignee: jhenner
        caseimportance: medium
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_provision_image_managed_azure():
    """
    Azure as of this test case date allows for provisioning from Managed
    Images.
    See RFE - https://bugzilla.redhat.com/show_bug.cgi?id=1452227
    See Create Manage Image - https://docs.microsoft.com/en-us/azure
    /virtual-machines/windows/capture-image-resource Section 1

    Bugzilla:
        1452227

    Polarion:
        assignee: jhenner
        casecomponent: Cloud
        initialEstimate: 1/4h
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_provision_from_private_image_azure():
    """
    1.Provision a VM using one private images

    Polarion:
        assignee: jhenner
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
        tags: provision
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_provision_market_place_image_azure():
    """
    1.Enable Marketplace images in Advanced settings
    2.Provision a VM using one

    Polarion:
        assignee: jhenner
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
        tags: provision
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_provision_fileshare_scvmm():
    """
    With 5.7.3 and 5.8.1 you can deploy templates onto scvmm registered
    File Shares.

    Polarion:
        assignee: jhenner
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.7
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_provision_host_maintenancemode_scvmm():
    """
    In scvmm, set qeblade26 into maintenance mode
    Refresh provider
    Attempt to provision to that host using auto placement.

    Polarion:
        assignee: jhenner
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.7
        upstream: yes
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_service_provision_managed_image_azure():
    """
    Bugzilla:
        1470491

    1. Provision Service using azure managed disk/image

    Polarion:
        assignee: jhenner
        casecomponent: Cloud
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_admin_username_azure():
    """
    Create provision request with username = "admin" - UI warning should
    appear

    Polarion:
        assignee: jhenner
        casecomponent: Infra
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/10h
        testtype: nonfunctional
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(2)
def test_create_provisioning_dialog_without_dialog_type():
    """
    Bugzilla:
        1344080

    Create provision dialog without selecting dialog type
    Automate - Customization - Provisioning dialog
    Configuration - Add a new dialog
    Provide name and description.
    Save
    Error should appear

    Polarion:
        assignee: jhenner
        casecomponent: Provisioning
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_auto_placement_provision_to_dvswitch_vlan_vmware():
    """
    Bugzilla:
        1467399

    Description of problem: issue appeared after 1458363
    Auto_placement provision into DVS vlan fails with Error "Destination
    placement_ds_name not provided]" if provider Network with the same
    name exists
    Version-Release number of selected component (if applicable):5.8.1
    Virtualcenter: 6.5
    How reproducible:100%
    Steps to Reproduce:
    1.Configure environment networks (check attachment)
    2.Provision VM with auto_placement
    3.Select DVS vlan
    Actual results:Provision fails
    Expected results: Provision should succeed and VM should be in
    selected vlan

    Polarion:
        assignee: jhenner
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass
