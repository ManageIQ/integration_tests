import pytest

from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.tier(3),
              pytest.mark.provider([LenovoProvider], scope="function")]


@pytest.fixture(scope="module")
def physical_rack(appliance, provider, setup_provider):
    try:
        # Get and return the first physical rack
        physical_racks = appliance.collections.physical_racks.filter({"provider": provider}).all()
        return physical_racks[0]
    except IndexError:
        pytest.skip("No rack resource on provider")


def test_physical_rack_details_dropdowns(physical_rack):
    """Navigate to the physical rack details page and verify the refresh button

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_rack.refresh()


def test_physical_racks_view_dropdowns(appliance, physical_rack):
    """Navigate to the physical racks page and verify that the dropdown menus are present

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_racks_view = navigate_to(appliance.collections.physical_racks, 'All')

    configuration_items = physical_racks_view.toolbar.configuration.items
    assert "Refresh Relationships and Power States" in configuration_items
