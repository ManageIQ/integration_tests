import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.manual, test_requirements.azure]


def test_vpc_env_selection():
    """
    Test selection of components in environment page of cloud instances
    with and without selected virtual private cloud

    Polarion:
        assignee: anikifor
        casecomponent: WebUI
        initialEstimate: 1/2h
        testSteps:
            1. Provision an Azure Instance from an Image.
            2. At the environment page, try to select components without vpc
            3. At the environment page, try to select components without vpc with vpc
        expectedResults:
            1. Instance provisioned and added successfully
            2. Items are selected successfully
            3. Items are selected successfully

    Bugzilla:
        1315945
    """
    pass


@pytest.mark.tier(2)
def test_refresh_azure_provider_with_empty_ipv6_config_on_vm():
    """
    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/4h
        setup: prepare azure  with https://mojo.redhat.com/docs/DOC-1145084 or
               https://docs.microsoft.com/en-us/azure/load-balancer/quickstart-create-basic-
               load-balancer-cli
        testSteps:
            1. refresh azure provider
        expectedResults:
            1. no errors found in logs
    Bugzilla:
        1468700
    """
    pass


@pytest.mark.tier(2)
def test_vm_terminate_deletedisk_azure():
    """
    New for 5.6.1, when terminating a VM in Azure, we need to go to the
    storage account and make sure the disk has also been removed.  You can
    check the VM details for the exact disk location prior to deleting.
    Note that Azure itself does not delete the disk when a VM is deleted,
    so this may initially cause some confusion.

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.6.1
        upstream: yes
    Bugzilla:
        1353306
    """
    pass


@pytest.mark.tier(1)
def test_refresh_with_empty_iot_hub_azure():
    """
    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: low
        initialEstimate: 1/6h
        setup: prepare env
               create an IoT Hub in Azure (using free tier pricing is good enough):
               $ az iot hub create --name rmanes-iothub --resource-group iot_rg
        testSteps:
            1. refresh azure provider
        expectedResults:
            1. no errors found in logs
    Bugzilla:
        1495318
    """
    pass


@pytest.mark.tier(2)
def test_regions_gov_azure():
    """
    This test verifies that Azure Government regions are not included in
    the default region list as most users will receive errors if they try
    to use them.
    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/8h
        setup: Check the region list when adding a Azure Provider.
        startsin: 5.7
    Bugzilla:
        1412363
    """
    pass


@pytest.mark.tier(1)
def test_regions_all_azure():
    """
    Need to validate the list of regions we show in the UI compared with
    regions.rb  Recent additions include UK South
    These really don"t change much, but you can use this test case id
    inside bugzilla to set qe_test flag.

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.6
    """
    pass


@pytest.mark.tier(1)
def test_regions_disable_azure():
    """
    CloudForms should be able to enable/disable unusable regions in Azure,
    like the Government one for example.

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/10h
        testSteps:
            1. Go into advanced settings and add or remove items from the following section.
               :ems_azure:
               :disabled_regions:
               - usgovarizona
               - usgoviowa
               - usgovtexas
               - usgovvirginia
    Bugzilla:
        1412355
    """
    pass


@pytest.mark.tier(1)
def test_public_ip_without_nic_azure():
    """
    Update testcase after BZ gets resolved
    Update: we are not filtering PIPs but we can use PIPs which are not
    associated to any NIC

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/6h
        testSteps:
            1. Have a Puplic IP on Azure which is not assigned to any Network
            Interface - such Public IPs should be reused property
            2. Provision Azure Instance - select public IP from 1.
    Bugzilla:
        1531099
    """
    pass


@pytest.mark.tier(1)
def test_sdn_nsg_arrays_refresh_azure():
    """
    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/6h
        testSteps:
            1. Add Network Security group on Azure with coma separated port ranges
            `1023,1025` rule inbound/outbound ( ATM this feature is not allowed in
            East US region of Azure - try West/Central)
            2. Add such Azure Region into CFME
            3. Refresh provider
    Bugzilla:
        1520196
    """
    pass


@pytest.mark.tier(2)
def test_provider_flavors_azure():
    """
    Verify that the vm flavors in Azure are of the correct sizes and that
    the size display in CFME is accurate.
    Low priority as it is unlikely to change once set.  Will want to check
    when azure adds new sizes.  Only need to spot check a few values.
    For current size values, you can check here:
    https://azure.microsoft.com/en-us/documentation/articles/virtual-
    machines-windows-sizes/

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: low
        initialEstimate: 1/8h
        startsin: 5.6
    Bugzilla:
        1357086
    """
    pass


@pytest.mark.tier(1)
def test_market_place_images_azure():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1491330

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/6h
        testSteps:
            1.Enable market place images
            2.Verify the list of images
    Bugzilla:
        1491330
    """
    pass
