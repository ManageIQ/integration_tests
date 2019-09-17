import pytest

from cfme import test_requirements

pytestmark = [test_requirements.replication]


@pytest.mark.manual
def test_replication_powertoggle():
    """
    power toggle from global to remote

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        caseimportance: critical
        initialEstimate: 1/12h
        testSteps:
            1. Have a VM created in the provider in the Remote region
               subscribed to Global.
            2. Turn the VM off using the Global appliance.
            3. Turn the VM on using the Global appliance.
        expectedResults:
            1.
            2. VM state changes to off in the Remote and Global appliance.
            3. VM state changes to on in the Remote and Global appliance.
.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_replication_appliance_add_single_subscription():
    """
    Add one remote subscription to global region

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        caseimportance: critical
        initialEstimate: 1/12h
        startsin: 5.7
        testSteps:
            1. Configure first appliance as Global.
            2. Configure second appliance as Remote, subscribed to Global.
        expectedResults:
            1.
            2. No error. Appliance subscribed.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_replication_delete_remote_from_global():
    """
    Delete remote subscription from global region

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        caseimportance: critical
        initialEstimate: 1/5h
        testSteps:
            1. Have A Remote subscribed to Global.
            2. Remove the Remote subscription from Global.
        expectedResults:
            1.
            2. No error. Appliance unsubscribed.
    """
    pass


@pytest.mark.manual
def test_replication_low_bandwidth():
    """
    ~5MB/s up/down

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_replication_re_add_deleted_remote():
    """
    Re-add deleted remote region

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        initialEstimate: 1/12h
        testSteps:
            1. Have A Remote subscribed to Global.
            2. Remove the Remote subscription from Global.
            3. Add the Remote to Global again
        expectedResults:
            1.
            2. No error. Appliance subscribed.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_replication_remote_to_global_by_ip_pglogical():
    """
    Test replication from remote region to global using any data type
    (provider,event,etc)

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        caseimportance: critical
        initialEstimate: 1/4h
        startsin: 5.6
        testSteps:
            1. Have A Remote subscribed to Global.
            2. Create a provider in remote region.
            3. Check the provider appeared in the Global.
        expectedResults:
            1.
            2.
            3. Provider appeared in the Global.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_replication_appliance_set_type_global_ui():
    """
    Set appliance replication type to "Global" and add subscription in the
    UI

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        caseimportance: critical
        initialEstimate: 1/6h
        testtype: functional
        testSteps:
            1. Have two appliances with same v2 keys and different regions
            2. Set one as Global and the other as Remote and add subscribe the
               Remote to the Global
        expectedResults:
            1.
            2. No error, appliance subscribed.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_replication_appliance_add_multi_subscription():
    """
    add two or more subscriptions to global

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        initialEstimate: 1/4h
        startsin: 5.7
        testSteps:
            1. Have three appliances with same v2 keys and different regions
            2. Set one as Global and the other two as Remote and add subscribe
               the Remotes to the Global
        expectedResults:
            1.
            2. appliances subscribed.
    """
    pass


@pytest.mark.manual
def test_replication_network_dropped_packets():
    """
    10% dropped packets

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_replication_global_region_dashboard():
    """
    Global dashboard show remote data

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        initialEstimate: 1/4h
        testSteps:
            1. Have a VM created in the provider in the Remote region which is
               subscribed to Global.
            2. Check the dashboard on the Global shows data from the Remote region.
        expectedResults:
            1.
            2. Dashboard on the Global displays data from the Remote region
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_replication_global_to_remote_new_vm_from_template():
    """
    Create a new VM from template in remote region from global region

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        caseimportance: critical
        initialEstimate: 1/6h
        testSteps:
            1. Configure first appliance as Global.
            2. Configure second appliance as Remote, subscribed to Global.
            3. Create a VM from template in Remote region using the Global appliance.
        expectedResults:
            1.
            2.
            3. VM created in the Remote, no errors.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_replication_subscription_revalidation_pglogical():
    """
    Subscription validation passes for replication subscriptions which
    have been validated and successfully saved.

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        caseimportance: medium
        initialEstimate: 1/12h
        testSteps:
            1. Attempt to validate the subscription
        expectedResults:
            1. Validation succeeds as this subscription was successfully
               saved and is currently replicating
    """
    pass
