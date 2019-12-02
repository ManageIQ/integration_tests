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
