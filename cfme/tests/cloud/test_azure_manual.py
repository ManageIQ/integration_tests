import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.manual, test_requirements.azure]


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
