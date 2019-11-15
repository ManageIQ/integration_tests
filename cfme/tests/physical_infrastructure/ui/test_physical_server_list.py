import pytest

from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.tier(3), pytest.mark.provider([LenovoProvider], scope="module")]


@pytest.fixture(scope="module")
def physical_server_collection(appliance, provider, setup_provider_modscope):
    # Get and return the physical server collection
    yield appliance.collections.physical_servers


def test_physical_servers_view_displayed(physical_server_collection):
    """Navigate to the physical servers page and verify that servers are displayed

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_servers_view = navigate_to(physical_server_collection, 'All')
    assert physical_servers_view.is_displayed


def test_physical_servers_view_dropdowns(physical_server_collection):
    """Navigate to the physical servers page and verify that the dropdown menus are present

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_servers_view = navigate_to(physical_server_collection, 'All')

    toolbar = physical_servers_view.toolbar

    assert toolbar.configuration.is_enabled
    assert toolbar.power.is_enabled
    assert toolbar.identify.is_enabled
    assert toolbar.policy.is_enabled
    assert toolbar.lifecycle.is_enabled

    configuration_items = toolbar.configuration.items
    configuration_options = [
        "Refresh Relationships and Power States",
    ]
    for option in configuration_options:
        assert option in configuration_items
        assert not toolbar.configuration.item_enabled(option)

    power_items = toolbar.power.items
    power_options = [
        "Power On",
        "Power Off",
        "Power Off Immediately",
        "Restart",
        "Restart Immediately"

    ]
    for option in power_options:
        assert option in power_items
        assert not toolbar.power.item_enabled(option)

    identify_items = toolbar.identify.items
    identify_options = [
        "Blink LED",
        "Turn On LED",
        "Turn Off LED",
    ]
    for option in identify_options:
        assert option in identify_items
        assert not toolbar.identify.item_enabled(option)

    policy_items = toolbar.policy.items
    policy_options = [
        "Manage Policies",
        "Edit Tags"
    ]
    for option in policy_options:
        assert option in policy_items
        assert not toolbar.policy.item_enabled(option)

    lifecycle_items = toolbar.lifecycle.items
    lifecycle_options = [
        "Provision Physical Server",
    ]
    for option in lifecycle_options:
        assert option in lifecycle_items
        assert not toolbar.lifecycle.item_enabled(option)
