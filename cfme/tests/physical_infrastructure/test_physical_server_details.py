# -*- coding: utf-8 -*-
import pytest

from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.wait import wait_for

pytestmark = [pytest.mark.tier(3)]

pytest_generate_tests = testgen.generate([LenovoProvider], scope="module")

@pytest.fixture(scope="module")
def physical_server(appliance, provider):
    # Create and then wait for the provider to be added
    provider.create()
    wait_for(
        lambda: provider.get_detail('Relationships', 'Physical Servers') != '0',
        fail_func=provider.refresh_provider_relationships_ui,
        num_sec=60, 
        delay=5
    )

    # Get and return the first physical server
    physical_servers = appliance.collections.physical_servers.all(provider)
    physical_server = physical_servers[0] 
    yield physical_server

    # Clean up the provider when finished
    provider.delete(cancel=False)
    provider.wait_for_delete()

def test_physical_server_details(physical_server):
    """Navigate to the physical server details page and verify that the page is displayed"""
    physical_server_view = navigate_to(physical_server, 'Details')
    assert physical_server_view.is_displayed

def test_physical_server_details_dropdowns(physical_server):
    """Navigate to the physical server details page and verify that the menus are present"""
    physical_server_view = navigate_to(physical_server, 'Details')

    configuration_items = physical_server_view.toolbar.configuration.items
    assert "Refresh Relationships and Power States" in configuration_items
    assert "Remove Physical Servers from Inventory" in configuration_items

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

def test_physical_server_details_stats(physical_server):
    """Navigate to the physical server details page and verify that the stats match"""
    physical_server.validate_stats(ui=True)
