# -*- coding: utf-8 -*-
import pytest

from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.physical.physical_server import PhysicalServerCollection
from cfme.physical.provider.lenovo import LenovoProvider
from cfme import test_requirements

pytestmark = [pytest.mark.tier(3)]

pytest_generate_tests = testgen.generate([LenovoProvider], scope="module")

@pytest.fixture(scope="module")
def physical_server_collection(appliance):
    return appliance.collections.physical_servers

def test_physical_server_details(physical_server_collection, provider):
    """Navigate to the physical server details page and verify that the page is displayed"""
    physical_servers = physical_server_collection.all(provider)
    physical_server = physical_servers[0]
    physical_server_view = navigate_to(physical_server, 'Details')
    assert physical_server_view.is_displayed


def test_physical_server_details_dropdowns(physical_server_collection, provider):
    """Navigate to the physical server details page and verify that the dropdown menus are present"""
    physical_servers = physical_server_collection.all(provider)
    physical_server = physical_servers[0]
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


def test_physical_server_details_stats(physical_server_collection, provider):
    """Navigate to the physical server details page and verify that the stats match"""
    physical_servers = physical_server_collection.all(provider)
    physical_servers[0].validate_stats(ui=True)
