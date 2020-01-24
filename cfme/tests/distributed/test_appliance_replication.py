from time import sleep

import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.long_running,
    test_requirements.distributed,
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE),
]


def configure_replication_appliances(appliances):
    """Configure two database-owning appliances, with unique region numbers,
    then set up database replication between them.
    """
    remote_app, global_app = appliances

    remote_app.configure(region=0)
    remote_app.wait_for_web_ui()

    global_app.configure(region=99, key_address=remote_app.hostname)
    global_app.wait_for_web_ui()

    remote_app.set_pglogical_replication(replication_type=':remote')
    global_app.set_pglogical_replication(replication_type=':global')
    global_app.add_pglogical_replication_subscription(remote_app.hostname)


def configure_distributed_appliances(appliances):
    """Configure one database-owning appliance, and a second appliance
       that connects to the database of the first.
    """
    appl1, appl2 = appliances
    appl1.configure(region=1)
    appl1.wait_for_web_ui()
    appl2.configure(region=1, key_address=appl1.hostname, db_address=appl1.hostname)
    appl2.wait_for_web_ui()


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_between_regions(provider, temp_appliances_unconfig_funcscope_rhevm):
    """Test that a provider added to the remote appliance is replicated to the global
    appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    configure_replication_appliances(temp_appliances_unconfig_funcscope_rhevm)
    remote_app, global_app = temp_appliances_unconfig_funcscope_rhevm

    remote_app.browser_steal = True
    with remote_app:
        provider.create()
        remote_app.collections.infra_providers.wait_for_a_provider()

    global_app.browser_steal = True
    with global_app:
        global_app.collections.infra_providers.wait_for_a_provider()
        assert provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_external_database_appliance(provider, temp_appliances_unconfig_funcscope_rhevm):
    """Test that a second appliance can be configured to join the region of the first,
    database-owning appliance, and that a provider created in the first appliance is
    visible in the web UI of the second appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    configure_distributed_appliances(temp_appliances_unconfig_funcscope_rhevm)

    appl1, appl2 = temp_appliances_unconfig_funcscope_rhevm
    appl1.browser_steal = True
    with appl1:
        provider.create()
        appl1.collections.infra_providers.wait_for_a_provider()

    appl2.browser_steal = True
    with appl2:
        appl2.collections.infra_providers.wait_for_a_provider()
        assert provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_database_disconnection(
        provider, temp_appliances_unconfig_funcscope_rhevm):
    """Test that a provider created on the remote appliance *after* a database restart on the
    global appliance is still successfully replicated to the global appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    configure_replication_appliances(temp_appliances_unconfig_funcscope_rhevm)
    remote_app, global_app = temp_appliances_unconfig_funcscope_rhevm

    global_app.db_service.stop()
    sleep(60)
    global_app.db_service.start()

    remote_app.browser_steal = True
    with remote_app:
        provider.create()
        remote_app.collections.infra_providers.wait_for_a_provider()

    global_app.browser_steal = True
    with global_app:
        global_app.collections.infra_providers.wait_for_a_provider()
        assert provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_database_disconnection_with_backlog(
        provider, temp_appliances_unconfig_funcscope_rhevm):
    """Test that a provider created on the remote appliance *before* a database restart on the
    global appliance is still successfully replicated to the global appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    configure_replication_appliances(temp_appliances_unconfig_funcscope_rhevm)
    remote_app, global_app = temp_appliances_unconfig_funcscope_rhevm

    remote_app.browser_steal = True
    with remote_app:
        provider.create()
        global_app.db_service.stop()
        sleep(60)
        global_app.db_service.start()
        remote_app.collections.infra_providers.wait_for_a_provider()

    global_app.browser_steal = True
    with global_app:
        global_app.collections.infra_providers.wait_for_a_provider()
        assert provider.exists


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
@pytest.mark.parametrize('create_vm', ['small_template'], indirect=True)
def test_distributed_vm_power_control(provider, create_vm,
        register_event, soft_assert, temp_appliances_unconfig_funcscope_rhevm):
    """Test that the global appliance can power off a VM managed by the remote appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    configure_replication_appliances(temp_appliances_unconfig_funcscope_rhevm)
    remote_app, global_app = temp_appliances_unconfig_funcscope_rhevm

    remote_app.browser_steal = True
    with remote_app:
        provider.create()
        remote_app.collections.infra_providers.wait_for_a_provider()

    global_app.browser_steal = True
    with global_app:
        register_event(target_type='VmOrTemplate', target_name=create_vm.name,
                       event_type='request_vm_poweroff')
        register_event(target_type='VmOrTemplate', target_name=create_vm.name,
                       event_type='vm_poweroff')

        create_vm.power_control_from_cfme(option=create_vm.POWER_OFF, cancel=False)
        navigate_to(create_vm.provider, 'Details')
        create_vm.wait_for_vm_state_change(desired_state=create_vm.STATE_OFF, timeout=900)
        soft_assert(create_vm.find_quadicon().data['state'] == 'off')
        soft_assert(
            not create_vm.mgmt.is_running,
            "vm running")
