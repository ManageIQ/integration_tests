import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.wait import TimedOutError

pytestmark = [
    test_requirements.sdn,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([OpenStackProvider], scope="module")
]


@pytest.fixture(scope='module')
def sec_group(appliance, provider):
    collection = appliance.collections.security_groups
    try:
        sec_group = collection.create(name=fauxfactory.gen_alphanumeric(),
                                      description=fauxfactory.gen_alphanumeric(),
                                      provider=provider,
                                      wait=True)
    except TimedOutError:
        pytest.fail('Timed out creating Security Groups')
    yield sec_group
    if sec_group.exists:
        sec_group.delete(wait=True)


@pytest.mark.tier(3)
def test_security_group_crud(sec_group):
    """ This will test whether it will create new Security Group and then deletes it.
    Steps:
        * Select Network Manager.
        * Provide Security groups name.
        * Provide Security groups Description.
        * Select Cloud Tenant.
        * Also delete it.

    Polarion:
        assignee: rhcf3_machine
        initialEstimate: 1/4h
        casecomponent: Cloud
    """
    # TODO: Update need to be done in future.
    assert sec_group.exists
    sec_group.delete(wait=True)
    assert not sec_group.exists


@pytest.mark.tier(3)
def test_security_group_create_cancel(appliance, provider):
    """ This will test cancelling on adding a security groups.

    Steps:
        * Select Network Manager.
        * Provide Security groups name.
        * Provide Security groups Description.
        * Select Cloud Tenant.
        * Cancel it.

    Polarion:
        assignee: rhcf3_machine
        initialEstimate: 1/4h
        casecomponent: Cloud
    """
    security_group = appliance.collections.security_groups
    sec_group = security_group.create(name=fauxfactory.gen_alphanumeric(),
                                      description=fauxfactory.gen_alphanumeric(),
                                      provider=provider,
                                      cancel=True)
    assert not sec_group.exists


@pytest.mark.manual
@test_requirements.azure
@pytest.mark.tier(1)
def test_sdn_nsg_firewall_rules_azure():
    """
    Bugzilla:
        1520196

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/12h
        testSteps:
            1. Add Network Security group on Azure with coma separated port ranges
            `1023,1025` rule inbound/outbound ( ATM this feature is not allowed in
            East US region of Azure - try West/Central)
            2. Add such Azure Region into CFME
            3. Refresh provider
            4. Open such NSG in CFME
        expectedResults:
            1.
            2.
            3.
            4. Check that ports from 1) do present in the UI as Firewall rules
    """
    pass


@test_requirements.ec2
@pytest.mark.manual
def test_security_group_record_values_ec2():
    """
    Bugzilla:
        1540283

    Polarion:
        assignee: mmojzis
        caseimportance: medium
        casecomponent: Cloud
        initialEstimate: 1/4h
        testSteps:
            1. Have an ec2 provider with a security group
            (which has all the possible values in records)
            2. Go to Networks -> Security groups
            3. Select a security group and go to its summary
        expectedResults:
            1.
            2.
            3. All traffic with All protocol are displayed as -1.
            When port range is All then Port and End port are displayed as 0.
            When port range is N/A then it's displayed also as 0.
            When source is IPV6 then record is not displayed at all!!!
            When record type is custom protocol then only its number is displayed.
    """
    pass
