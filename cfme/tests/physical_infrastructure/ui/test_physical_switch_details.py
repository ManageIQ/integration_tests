import pytest

from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.tier(3), pytest.mark.provider([LenovoProvider], scope="module")]


@pytest.fixture(scope="module")
def physical_switch(appliance, setup_provider_modscope):
    # Get and return the first physical switch
    physical_switches = appliance.collections.physical_switches.all()
    return physical_switches[0]


def test_physical_switch_details(physical_switch):
    """Navigate to the physical switch details page and verify that the page is displayed

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_switch_view = navigate_to(physical_switch, 'Details')
    assert physical_switch_view.is_displayed


def test_physical_switch_details_dropdowns(physical_switch):
    """Navigate to the physical switch details page and verify that the menus are present

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_switch_view = navigate_to(physical_switch, 'Details')

    configuration_items = physical_switch_view.toolbar.configuration.items
    assert "Refresh Relationships and Power States" in configuration_items
