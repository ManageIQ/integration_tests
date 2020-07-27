from time import sleep

import fauxfactory
import pytest
from widgetastic.exceptions import NoSuchElementException

from cfme import test_requirements
from cfme.base.ui import LoginPage
from cfme.cloud.provider import CloudProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import InfraVmDetailsView
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.tests.configure.test_zones import create_zone
from cfme.utils import conf
from cfme.utils.appliance import ViaREST
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import cfme_data
from cfme.utils.rest import assert_response
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE)
]

HTTPD_ROLES = ('cockpit_ws', 'user_interface', 'remote_console', 'web_services')


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
@test_requirements.multi_region
def test_appliance_replicate_between_regions(provider, replicated_appliances):
    """Test that a provider added to the remote appliance is replicated to the global
    appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    remote_appliance, global_appliance = replicated_appliances

    with remote_appliance:
        provider.create()
        remote_appliance.collections.infra_providers.wait_for_a_provider()

    with global_appliance:
        global_appliance.collections.infra_providers.wait_for_a_provider()
        assert provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
@test_requirements.distributed
def test_external_database_appliance(provider, distributed_appliances):
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
    primary_appliance, secondary_appliance = distributed_appliances

    with primary_appliance:
        provider.create()
        primary_appliance.collections.infra_providers.wait_for_a_provider()

    with secondary_appliance:
        secondary_appliance.collections.infra_providers.wait_for_a_provider()
        assert provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
@test_requirements.multi_region
def test_appliance_replicate_database_disconnection(provider, replicated_appliances):
    """Test that a provider created on the remote appliance *after* a database restart on the
    global appliance is still successfully replicated to the global appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    remote_appliance, global_appliance = replicated_appliances

    global_appliance.db_service.stop()
    sleep(60)
    global_appliance.db_service.start()

    with remote_appliance:
        provider.create()
        remote_appliance.collections.infra_providers.wait_for_a_provider()

    with global_appliance:
        global_appliance.collections.infra_providers.wait_for_a_provider()
        assert provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
@test_requirements.multi_region
def test_appliance_replicate_database_disconnection_with_backlog(provider, replicated_appliances):
    """Test that a provider created on the remote appliance *before* a database restart on the
    global appliance is still successfully replicated to the global appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    remote_appliance, global_appliance = replicated_appliances

    with remote_appliance:
        provider.create()
        global_appliance.db_service.stop()
        sleep(60)
        global_appliance.db_service.start()
        remote_appliance.collections.infra_providers.wait_for_a_provider()

    with global_appliance:
        global_appliance.collections.infra_providers.wait_for_a_provider()
        assert provider.exists


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
@pytest.mark.provider([CloudProvider, InfraProvider], selector=ONE_PER_TYPE)
@test_requirements.multi_region
@test_requirements.power
def test_replication_vm_power_control(provider, create_vm, context, replicated_appliances):
    """Test that the global appliance can power off a VM managed by the remote appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    remote_appliance, global_appliance = replicated_appliances

    vm_per_appliance = {
        a: a.provider_based_collection(provider).instantiate(create_vm.name, provider)
        for a in replicated_appliances
    }

    with remote_appliance:
        assert provider.create(validate_inventory=True), "Could not create provider."

    with global_appliance:
        vm = vm_per_appliance[global_appliance]
        if context.name == 'UI':
            vm.power_control_from_cfme(option=vm.POWER_OFF, cancel=False)
        else:
            vm_entity = global_appliance.rest_api.collections.vms.get(name=vm.name)
            global_appliance.rest_api.collections.vms.action.stop(vm_entity)
            assert_response(global_appliance, task_wait=0)

    with remote_appliance:
        vm = vm_per_appliance[remote_appliance]
        vm.wait_for_vm_state_change(desired_state=vm.STATE_OFF, timeout=900)
        assert vm.find_quadicon().data['state'] == 'off', "Incorrect VM quadicon state"
        assert not vm.mgmt.is_running, "VM is still running"


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1678142])
@pytest.mark.ignore_stream('upstream')
@test_requirements.multi_region
def test_replication_connect_to_vm_in_region(provider, replicated_appliances):
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
    remote_appliance, global_appliance = replicated_appliances

    vm_name = provider.data['cap_and_util']['chargeback_vm']

    vm_per_appliance = {
        a: a.provider_based_collection(provider).instantiate(vm_name, provider)
        for a in replicated_appliances
    }

    with remote_appliance:
        provider.create()
        remote_appliance.collections.infra_providers.wait_for_a_provider()

    with global_appliance:
        view = navigate_to(vm_per_appliance[global_appliance], 'Details')

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

        # Use VM instantiated on global_appliance here because we're still using the same browser.
        view = vm_per_appliance[global_appliance].create_view(InfraVmDetailsView)
        wait_for(lambda: view.is_displayed, message="Wait for VM Details page")


@pytest.mark.ignore_stream("upstream")
@test_requirements.distributed
def test_appliance_httpd_roles(distributed_appliances):
    """Test that a secondary appliance only runs httpd if a server role requires it.
    Disable all server roles that require httpd, and verify that httpd is stopped. For each server
    role that requires httpd, enable it (with all other httpd server roles disabled), and verify
    that httpd starts.

    Bugzilla:
        1449766

    Metadata:
        test_flag: configuration

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/4h
    """
    primary_appliance, secondary_appliance = distributed_appliances

    fill_values = {k: False for k in HTTPD_ROLES}

    # Change roles through primary appliance to guarantee UI availability.
    sid = secondary_appliance.server.sid
    secondary_server = primary_appliance.collections.servers.instantiate(sid=sid)

    with primary_appliance:
        view = navigate_to(secondary_server, 'Server')

        for role in HTTPD_ROLES:
            # Disable all httpd roles and verify that httpd is stopped.
            view.server_roles.fill(fill_values)
            view.save.click()
            view.flash.assert_no_error()

            wait_for(lambda: not secondary_appliance.httpd.running, delay=10)

            # Enable single httpd role and verify that httpd is running.
            view.server_roles.fill({role: True})
            view.save.click()
            view.flash.assert_no_error()

            wait_for(lambda: secondary_appliance.httpd.running, delay=10)


@pytest.mark.ignore_stream("upstream")
@test_requirements.distributed
def test_appliance_reporting_role(distributed_appliances):
    """Test that a report queued from an appliance with the User Interface role but not the
    Reporting role gets successfully run by a worker appliance that does have the Reporting
    role.

    Bugzilla:
        1629945

    Metadata:
        test_flag: configuration

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/4h
    """
    primary_appliance, secondary_appliance = distributed_appliances

    # Disable the Reporting role on the primary appliance.
    primary_appliance.server.settings.disable_server_roles('reporting')

    # Wait for the role to be disabled in the database.
    wait_for(lambda: not primary_appliance.server.settings.server_roles_db['reporting'])

    # Queue the report and wait for it to complete.
    primary_appliance.collections.reports.instantiate(
        type="Operations",
        subtype="EVM",
        menu_name="EVM Server UserID Usage Report"
    ).queue(wait_for_finish=True)


@pytest.mark.ignore_stream('upstream')
@test_requirements.distributed
def test_server_role_failover(distributed_appliances):
    """Test that server roles failover successfully to a secondary appliance if evmserverd stops
    on the primary appliance.

    Metadata:
        test_flag: configuration

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    primary_appliance, secondary_appliance = distributed_appliances

    all_server_roles = cfme_data.get('server_roles', {'all': []})['all']
    if not all_server_roles:
        pytest.skip('Empty server_roles dictionary in cfme_data, skipping test')

    # Remove roles in cfme_data that are not in 5.11 or later.
    remove_roles = ['websocket']
    server_roles = [r for r in all_server_roles if r not in remove_roles]
    fill_values = {k: True for k in server_roles}

    # Enable all roles on both appliances.
    for appliance in distributed_appliances:
        with appliance:
            view = navigate_to(appliance.server, 'Server')
            view.server_roles.fill(fill_values)
            view.save.click()
            view.flash.assert_no_error()

    # Stop evmserverd on secondary appliance.
    secondary_appliance.evmserverd.stop()

    # Verify that all roles are active on primary appliance.
    wait_for(lambda: primary_appliance.server_roles == fill_values)

    # Stop evmserverd on primary appliance and restart it on secondary appliance.
    secondary_appliance.evmserverd.start()
    primary_appliance.evmserverd.stop()

    # Verify that all roles are now active on secondary appliance.
    wait_for(lambda: secondary_appliance.server_roles == fill_values)


@pytest.mark.ignore_stream("upstream")
@test_requirements.multi_region
def test_appliance_replicate_zones(replicated_appliances):
    """
    Verify that no remote zones can be selected when changing the server's zone
    in the global appliance UI.

    Bugzilla:
        1470283

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
    """
    remote_appliance, global_appliance = replicated_appliances

    remote_zone = 'remote-A'
    remote_appliance.collections.zones.create(name=remote_zone, description=remote_zone)

    global_zone = 'global-A'
    global_appliance.collections.zones.create(name=global_zone, description=global_zone)

    with global_appliance:
        view = navigate_to(global_appliance.server, 'Server')
        global_zones = [o.text for o in view.basic_information.appliance_zone.all_options]
        assert global_zone in global_zones and remote_zone not in global_zones


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(automates=[1796681])
@test_requirements.multi_region
def test_appliance_replicate_remote_down(replicated_appliances):
    """Test that the Replication tab displays in the global appliance UI when the remote appliance
    database cannot be reached.

    Bugzilla:
        1796681

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    remote_appliance, global_appliance = replicated_appliances

    with global_appliance:
        global_region = global_appliance.server.zone.region
        assert global_region.replication.get_replication_status(host=remote_appliance.hostname), (
            "Remote appliance not found on Replication tab after initial configuration.")

        result = global_appliance.ssh_client.run_command(
            f"firewall-cmd --direct --add-rule ipv4 filter OUTPUT 0 -d {remote_appliance.hostname}"
            " -j DROP")
        assert result.success, "Could not create firewall rule on global appliance."

        global_appliance.browser.widgetastic.refresh()
        assert global_region.replication.get_replication_status(host=remote_appliance.hostname), (
            "Remote appliance not found on Replication tab after dropped connection.")


@pytest.mark.tier(3)
@pytest.mark.parametrize('location', ['zone', 'region'], ids=['from_zone', 'from_region'])
def test_distributed_delete_appliance(distributed_appliances, location):
    """In a distributed appliance configuration, shut down the secondary appliance, and verify that
    the server record can be deleted from either the zone's or the region's Diagnostics page.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        initialEstimate: 1/2h
    """
    primary_appliance, secondary_appliance = distributed_appliances

    secondary_server = primary_appliance.collections.servers.instantiate(
        sid=secondary_appliance.server.sid)

    secondary_appliance.evmserverd.stop()

    with primary_appliance:
        if location == 'zone':
            dest = primary_appliance.server.zone
        else:
            dest = primary_appliance.server.zone.region

        # Delete stopped server from region or zone diagnostics page
        view = navigate_to(dest, 'RolesByServers')
        server_string = f'{secondary_server.name} [{secondary_server.sid}]'
        view.rolesbyservers.tree.click_path(f'Server: {server_string} (stopped)')
        view.rolesbyservers.configuration.item_select(
            f'Delete Server {server_string}', handle_alert=True)

        # Flash message appears when deleting server from zone page, but not from region page
        if location == 'zone':
            view.flash.assert_success_message(f'Server "{server_string}": Delete successful')

        view.browser.refresh()
        # Server is removed from Roles By Servers tab's tree
        assert not any(e.text.startswith(f'Server: {server_string}') for e in
            view.rolesbyservers.tree.root_items)
        # Server is removed from Diagnostics tree
        assert not any(e.text.startswith(f'Server: {server_string}') for e in
            view.accordions.diagnostics.tree.root_items)
        # Server is removed from Settings tree
        assert not secondary_server.exists


@pytest.mark.tier(1)
def test_distributed_zone_delete_occupied(distributed_appliances):
    """Verify that zone with appliances in it cannot be deleted.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/12h
    """
    _, secondary_appliance = distributed_appliances

    with secondary_appliance:
        # Create new zone
        zone = create_zone(secondary_appliance, fauxfactory.gen_alphanumeric(),
                           fauxfactory.gen_alphanumeric())

        # Add secondary appliance to new zone
        server_info = secondary_appliance.server.settings
        server_info.update_basic_information({'appliance_zone': zone.name})

        with pytest.raises(NoSuchElementException):
            zone.delete()
        assert zone.exists, "Occupied zone was deleted"

        server_info.update_basic_information({'appliance_zone': 'default'})

        zone.delete()
        assert not zone.exists, "Zone could not be deleted"
