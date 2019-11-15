import pytest

from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.tier(3), pytest.mark.provider([LenovoProvider], scope="module")]


def test_physical_switches_view_displayed(appliance, physical_switch):
    """Navigate to the physical switches page and verify that switches are displayed

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_switches_view = navigate_to(appliance.collections.physical_switches, 'All')
    assert physical_switches_view.is_displayed


def test_physical_switches_view_dropdowns(appliance, physical_switch):
    """Navigate to the physical switches page and verify that the dropdown menus are present

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_switches_view = navigate_to(appliance.collections.physical_switches, 'All')

    toolbar = physical_switches_view.toolbar

    assert toolbar.configuration.is_enabled

    configuration_items = toolbar.configuration.items
    configuration_options = [
        "Refresh Relationships and Power States",
    ]

    for option in configuration_options:
        assert option in configuration_items
        assert not toolbar.configuration.item_enabled(option)
