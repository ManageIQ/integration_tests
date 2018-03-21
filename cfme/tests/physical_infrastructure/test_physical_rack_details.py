# -*- coding: utf-8 -*-
import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.physical.provider.lenovo import LenovoProvider

pytestmark = [pytest.mark.tier(3), pytest.mark.provider([LenovoProvider], scope="function")]


@pytest.fixture(scope="module")
def physical_rack(appliance, provider, setup_provider_modscope):
    # Get and return the first physical rack
    physical_racks = appliance.collections.physical_racks.filter({"provider": provider}).all()
    return physical_racks[0]


def test_physical_rack_details(physical_rack):
    """Navigate to the physical rack details page and verify that the page is displayed"""
    physical_rack_view = navigate_to(physical_rack, 'Details')
    assert physical_rack_view.is_displayed


def test_physical_rack_details_dropdowns(physical_rack):
    """Navigate to the physical rack details page and verify that the menus are present"""
    physical_rack_view = navigate_to(physical_rack, 'Details')

    configuration_items = physical_rack_view.toolbar.configuration.items
    assert "Refresh Relationships and Power States" in configuration_items
