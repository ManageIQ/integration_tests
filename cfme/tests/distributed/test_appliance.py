import fauxfactory
import pytest
from selenium.common.exceptions import NoSuchElementException

from cfme import test_requirements
from cfme.configure.configuration.server_settings import ServerInformation
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.tests.configure.test_zones import create_zone
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import cfme_data
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    test_requirements.distributed,
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE),
]

HTTPD_ROLES = ('cockpit_ws', 'user_interface', 'remote_console', 'web_services')


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_external_database_appliance(provider, distributed_appliances):
    """Test that a second appliance can be configured to join the region of the first,
    database-owning appliance, and that a provider created in the first appliance is
    visible in the web UI of the second appliance.

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


@pytest.mark.ignore_stream("upstream")
def test_appliance_httpd_roles(distributed_appliances):
    """Test that a secondary appliance only runs httpd if a server role requires it.
    Disable all server roles that require httpd, and verify that httpd is stopped. For each server
    role that requires httpd, enable it (with all other httpd server roles disabled), and verify
    that httpd starts.

    Bugzilla:
        1449766

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
def test_appliance_reporting_role(distributed_appliances):
    """Test that a report queued from an appliance with the User Interface role but not the
    Reporting role gets successfully run by a worker appliance that does have the Reporting
    role.

    Bugzilla:
        1629945

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
def test_server_role_failover(distributed_appliances):
    """Test that server roles failover successfully to a secondary appliance if evmserverd stops
    on the primary appliance.

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


@pytest.mark.tier(1)
def test_distributed_zone_delete_occupied(distributed_appliances):
    """Verify that zone with appliances in it cannot be deleted.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/12h
    """
    primary_appliance, secondary_appliance = distributed_appliances

    with primary_appliance:
        # Create new zone
        zone_name = fauxfactory.gen_alphanumeric()
        zone_desc = fauxfactory.gen_alphanumeric()
        zone = create_zone(primary_appliance, zone_name, zone_desc)

        # Add secondary appliance to new zone
        server_info = ServerInformation(secondary_appliance)
        server_info.update_basic_information({'appliance_zone': zone.name})

        with pytest.raises(NoSuchElementException):
            zone.delete()
        assert zone.exists, "Occupied zone was deleted"

        server_info.update_basic_information({'appliance_zone': 'default'})

        zone.delete()
        assert not zone.exists, "Zone could not be deleted"
