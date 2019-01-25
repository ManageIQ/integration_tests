import pytest

from cfme import test_requirements

@pytest.mark.manual
@test_requirements.rep
def test_replication_powertoggle():
    """
    power toggle from global to remote

    Polarion:
        assignee: jhenner
        casecomponent: Infra
        caseimportance: critical
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.rep
def test_replication_central_admin_vm_retirement():
    """
    retire a vm via CA

    Polarion:
        assignee: jhenner
        casecomponent: Infra
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_replication_central_admin_service_provisioning():
    """
    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(2)
def test_replication_appliance_add_single_subscription():
    """
    Add one remote subscription to global region

    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        caseimportance: critical
        initialEstimate: 1/12h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(3)
def test_replication_delete_remote_from_global():
    """
    Delete remote subscription from global region

    Polarion:
        assignee: jhenner
        casecomponent: Infra
        caseimportance: critical
        initialEstimate: 1/5h
    """
    pass


@pytest.mark.manual
def test_replication_low_bandwidth():
    """
    ~5MB/s up/down

    Polarion:
        assignee: jhenner
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(3)
def test_replication_re_add_deleted_remote():
    """
    Re-add deleted remote region

    Polarion:
        assignee: jhenner
        casecomponent: Infra
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_replication_central_admin_ansible_playbook_service_from_global():
    """
    Playbook service is ordered from the master region catalog.

    Polarion:
        assignee: tpapaioa
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_replication_remote_to_global_by_ip_pglogical():
    """
    Test replication from remote region to global using any data type
    (provider,event,etc)

    Polarion:
        assignee: jhenner
        casecomponent: Infra
        caseimportance: critical
        initialEstimate: 1/4h
        startsin: 5.6
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_replication_appliance_set_type_global_ui():
    """
    Set appliance replication type to "Global" and add subscription in the
    UI

    Polarion:
        assignee: jhenner
        casecomponent: Infra
        caseimportance: critical
        initialEstimate: 1/6h
        testtype: integration
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(2)
def test_replication_appliance_add_multi_subscription():
    """
    add two or more subscriptions to global

    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        initialEstimate: 1/4h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_replication_appliance_set_type_remote_ui():
    """
    Can the appliance be set to the "remote" type in the ui

    Polarion:
        assignee: jhenner
        casecomponent: Infra
        caseimportance: critical
        initialEstimate: 1/12h
        testtype: integration
    """
    pass


@pytest.mark.manual
def test_replication_network_dropped_packets():
    """
    10% dropped packets

    Polarion:
        assignee: jhenner
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_replication_global_region_dashboard():
    """
    Global dashboard show remote data

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.rep
@pytest.mark.tier(1)
def test_replication_global_to_remote_new_vm_from_template():
    """
    Create a new VM from template in remote region from global region

    Polarion:
        assignee: jhenner
        casecomponent: Provisioning
        caseimportance: critical
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.rep
def test_replication_central_admin_vm_reconfigure():
    """
    reconfigure a VM via CA

    Polarion:
        assignee: jhenner
        casecomponent: Infra
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_replication_central_admin_adhoc_provision_template():
    """
    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_replication_subscription_revalidation_pglogical():
    """
    Subscription validation passes for replication subscriptions which
    have been validated and successfully saved.

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
        testSteps:
            1. Attempt to validate the subscription
        expectedResults:
            1. Validation succeeds as this subscription was successfully
               saved and is currently replicating
    """
    pass
