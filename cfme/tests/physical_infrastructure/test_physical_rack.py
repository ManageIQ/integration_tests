# -*- coding: utf-8 -*-
import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.physical.provider.lenovo import LenovoProvider

pytestmark = [pytest.mark.tier(3), pytest.mark.provider([LenovoProvider], scope="function")]


@pytest.fixture(scope="module")
def physical_rack(appliance, provider, setup_provider):
    try:
        # Get and return the first physical rack
        physical_racks = appliance.collections.physical_racks.filter({"provider": provider}).all()
        return physical_racks[0]
    except IndexError:
        pytest.skip("No rack resource found")


def test_physical_rack_details_dropdowns(physical_rack):
    """Navigate to the physical rack details page and verify the refresh button"""
    physical_rack.refresh()


def physical_rack_collection(appliance, provider, setup_provider_modscope):
    # Get and return the physical rack collection
    return appliance.collections.physical_racks


def test_physical_racks_view_dropdowns(physical_rack_collection):
    """Navigate to the physical racks page and verify that the dropdown menus are present"""
    physical_racks_view = navigate_to(physical_rack_collection, 'All')

    configuration_items = physical_racks_view.toolbar.configuration.items
    assert "Refresh Relationships and Power States" in configuration_items
