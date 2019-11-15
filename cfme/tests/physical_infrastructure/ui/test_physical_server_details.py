import pytest

from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.tier(3), pytest.mark.provider([LenovoProvider], scope="module")]


@pytest.fixture(scope="module")
def physical_server(appliance, provider, setup_provider_modscope):
    # Get and return the first physical server
    physical_servers = appliance.collections.physical_servers.all(provider)
    yield physical_servers[0]


def test_physical_server_details(physical_server):
    """Navigate to the physical server details page and verify that the page is displayed

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_server_view = navigate_to(physical_server, 'Details')
    assert physical_server_view.is_displayed


def test_physical_server_details_dropdowns(physical_server):
    """Navigate to the physical server details page and verify that the menus are present

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_server_view = navigate_to(physical_server, 'Details')

    configuration_items = physical_server_view.toolbar.configuration.items
    assert "Refresh Relationships and Power States" in configuration_items

    power_items = physical_server_view.toolbar.power.items
    assert "Power On" in power_items
    assert "Power Off" in power_items
    assert "Power Off Immediately" in power_items
    assert "Restart" in power_items
    assert "Restart Immediately" in power_items
    assert "Restart to System Setup" in power_items
    assert "Restart Management Controller" in power_items

    identify_items = physical_server_view.toolbar.identify.items
    assert "Blink LED" in identify_items
    assert "Turn On LED" in identify_items
    assert "Turn Off LED" in identify_items

    policy_items = physical_server_view.toolbar.policy.items
    assert "Manage Policies" in policy_items
    assert "Edit Tags" in policy_items

    lifecycle_items = physical_server_view.toolbar.lifecycle.items
    assert "Provision Physical Server" in lifecycle_items

    monitoring_items = physical_server_view.toolbar.monitoring.items
    assert "Timelines" in monitoring_items


def test_network_devices(physical_server):
    """Navigate to the Network Devices page and verify that the page is displayed

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """

    num_network_devices = physical_server.num_network_devices()
    network_device_view = navigate_to(physical_server, 'NetworkDevices')

    assert(network_device_view.is_displayed if num_network_devices != "0" else
           not network_device_view.is_displayed)


def test_storage_devices(physical_server):
    """Navigate to the Storage Devices page and verify that the page is displayed

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """

    num_storage_devices = physical_server.num_storage_devices()
    storage_device_view = navigate_to(physical_server, 'StorageDevices')

    assert(storage_device_view.is_displayed if num_storage_devices != "0" else
           not storage_device_view.is_displayed)


def test_physical_server_details_stats(physical_server):
    """Navigate to the physical server details page and verify that the stats match

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_server.validate_stats(ui=True)
