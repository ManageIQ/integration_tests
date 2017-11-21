# -*- coding: utf-8 -*-
import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.physical.provider.lenovo import LenovoProvider
from cfme import test_requirements

pytestmark = [pytest.mark.tier(3), pytest.mark.provider([LenovoProvider], scope="module")]

pytest_generate_tests = testgen.generate([LenovoProvider], scope="module")

@pytest.fixture(scope="module")
def physical_server_collection(appliance, provider, setup_provider_modscope):
    # Get and return the physical server collection
    yield appliance.collections.physical_servers


def test_physical_servers_view_displayed(physical_server_collection):
    """Navigate to the physical servers page and verify that servers are displayed"""
    physical_servers_view = navigate_to(physical_server_collection, 'All')
    assert physical_servers_view.is_displayed

def test_physical_servers_view_dropdowns(physical_server_collection):
    """Navigate to the physical servers page and verify that the dropdown menus are present"""
    physical_servers_view = navigate_to(physical_server_collection, 'All')

    configuration_items = physical_servers_view.toolbar.configuration.items
    assert "Refresh Relationships and Power States" in configuration_items
    assert "Remove Physical Servers from Inventory" in configuration_items

    power_items = physical_servers_view.toolbar.power.items
    assert "Power On" in power_items
    assert "Power Off" in power_items
    assert "Power Off Immediately" in power_items
    assert "Restart" in power_items
    assert "Restart Immediately" in power_items
    assert "Restart to System Setup" in power_items
    assert "Restart Management Controller" in power_items

    identify_items = physical_servers_view.toolbar.identify.items
    assert "Blink LED" in identify_items
    assert "Turn On LED" in identify_items
    assert "Turn Off LED" in identify_items

    policy_items = physical_servers_view.toolbar.policy.items
    assert "Manage Policies" in policy_items
    assert "Edit Tags" in policy_items

    lifecycle_items = physical_servers_view.toolbar.lifecycle.items
    assert "Provision Physical Server" in lifecycle_items
