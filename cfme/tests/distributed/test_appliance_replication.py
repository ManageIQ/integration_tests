from time import sleep

import pytest

from cfme import test_requirements
from cfme.base.ui import LoginPage
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import InfraVmDetailsView
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils import conf
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    test_requirements.distributed,
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE),
]


def configure_replication_appliances(remote_app, global_app):
    """Configure a database-owning appliance, with global region #99,
    sharing the same encryption key as the preconfigured appliance. with remote region #0.
    Then set up database replication between them.
    """
    logger.info("Starting appliance replication configuration.")
    global_app.configure(region=99, key_address=remote_app.hostname)

    remote_app.set_pglogical_replication(replication_type=':remote')
    global_app.set_pglogical_replication(replication_type=':global')
    global_app.add_pglogical_replication_subscription(remote_app.hostname)
    logger.info("Finished appliance replication configuration.")


def configure_distributed_appliances(primary_app, secondary_app):
    """Configure one database-owning appliance, and a second appliance
       that connects to the database of the first.
    """
    secondary_app.configure(region=0,
        key_address=primary_app.hostname, db_address=primary_app.hostname)


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_between_regions(provider,
        temp_appliance_preconfig_funcscope_rhevm, temp_appliance_unconfig_funcscope_rhevm):
    """Test that a provider added to the remote appliance is replicated to the global
    appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    remote_app = temp_appliance_preconfig_funcscope_rhevm
    global_app = temp_appliance_unconfig_funcscope_rhevm

    configure_replication_appliances(remote_app, global_app)

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
def test_external_database_appliance(provider,
        temp_appliance_preconfig_funcscope_rhevm, temp_appliance_unconfig_funcscope_rhevm):
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
    primary_app = temp_appliance_preconfig_funcscope_rhevm
    secondary_app = temp_appliance_unconfig_funcscope_rhevm

    configure_distributed_appliances(primary_app, secondary_app)

    primary_app.browser_steal = True
    with primary_app:
        provider.create()
        primary_app.collections.infra_providers.wait_for_a_provider()

    secondary_app.browser_steal = True
    with secondary_app:
        secondary_app.collections.infra_providers.wait_for_a_provider()
        assert provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_database_disconnection(provider,
        temp_appliance_preconfig_funcscope_rhevm, temp_appliance_unconfig_funcscope_rhevm):
    """Test that a provider created on the remote appliance *after* a database restart on the
    global appliance is still successfully replicated to the global appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    remote_app = temp_appliance_preconfig_funcscope_rhevm
    global_app = temp_appliance_unconfig_funcscope_rhevm

    configure_replication_appliances(remote_app, global_app)

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
def test_appliance_replicate_database_disconnection_with_backlog(provider,
        temp_appliance_preconfig_funcscope_rhevm, temp_appliance_unconfig_funcscope_rhevm):
    """Test that a provider created on the remote appliance *before* a database restart on the
    global appliance is still successfully replicated to the global appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    remote_app = temp_appliance_preconfig_funcscope_rhevm
    global_app = temp_appliance_unconfig_funcscope_rhevm

    configure_replication_appliances(remote_app, global_app)

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
        register_event, soft_assert, temp_appliance_preconfig_funcscope_rhevm,
        temp_appliance_unconfig_funcscope_rhevm):
    """Test that the global appliance can power off a VM managed by the remote appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    remote_app = temp_appliance_preconfig_funcscope_rhevm
    global_app = temp_appliance_unconfig_funcscope_rhevm

    configure_replication_appliances(remote_app, global_app)

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


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1678142])
@pytest.mark.ignore_stream('upstream', '5.10')
def test_replication_connect_to_vm_in_region(provider,
        temp_appliance_preconfig_funcscope_rhevm, temp_appliance_unconfig_funcscope_rhevm):
    """Test that the user can view the VM in the global appliance UI, click on the
    "Connect to VM in its Region" button, and be redirected to the VM in the remote appliance UI.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
        startsin: 5.11
    """
    remote_appliance = temp_appliance_preconfig_funcscope_rhevm
    global_appliance = temp_appliance_unconfig_funcscope_rhevm

    configure_replication_appliances(remote_appliance, global_appliance)

    vm_name = provider.data['cap_and_util']['chargeback_vm']

    remote_appliance.browser_steal = True
    with remote_appliance:
        provider.create()
        remote_appliance.collections.infra_providers.wait_for_a_provider()

    global_appliance.browser_steal = True
    with global_appliance:
        collection = global_appliance.provider_based_collection(provider)
        vm = collection.instantiate(vm_name, provider)
        view = navigate_to(vm, 'Details')

        initial_count = len(view.browser.window_handles)
        main_window = view.browser.current_window_handle

        view.entities.summary('Multi Region').click_at('Remote Region')

        wait_for(
            lambda: len(view.browser.window_handles) > initial_count,
            timeout=30,
            message="Check for new browser window",
        )
        open_url_window = (set(view.browser.window_handles) - {main_window}).pop()
        view.browser.switch_to_window(open_url_window)

        # TODO: Remove this once `ensure_page_safe()` is equipped to handle WebDriverException
        # When a new window opens, URL takes time to load, this will act as a workaround.
        sleep(5)

        view = global_appliance.browser.create_view(LoginPage)
        wait_for(lambda: view.is_displayed, message="Wait for Login page")
        view.fill({
            'username': conf.credentials['default']['username'],
            'password': conf.credentials['default']['password']
        })
        view.login.click()
        view = vm.create_view(InfraVmDetailsView)
        wait_for(lambda: view.is_displayed, message="Wait for VM Details page")


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(automates=[1678142])
def test_appliance_replicate_remote_down(temp_appliance_preconfig_funcscope_rhevm,
       temp_appliance_unconfig_funcscope_rhevm):
    """Test that the Replication tab displays in the global appliance UI when the remote appliance
    is down.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
        startsin: 5.11
    """
    remote_appliance = temp_appliance_preconfig_funcscope_rhevm
    global_appliance = temp_appliance_unconfig_funcscope_rhevm

    configure_replication_appliances(remote_appliance, global_appliance)

    global_region = global_appliance.server.zone.region
    assert global_region.replication.get_replication_status(host=remote_appliance.hostname), (
        "Remote appliance not found on global appliance's Replication tab.")

    logger.info("Stopping remote appliance database.")
    remote_appliance.db_service.stop()
    logger.info("Stopped remote appliance database.")

    assert global_region.replication.get_replication_status(host=remote_appliance.hostname), (
        "Remote appliance not found on global appliance's Replication tab after database stop.")
