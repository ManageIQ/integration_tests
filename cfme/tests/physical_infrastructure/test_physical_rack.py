# -*- coding: utf-8 -*-
import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.physical.provider.lenovo import LenovoProvider

pytestmark = [pytest.mark.tier(3), pytest.mark.provider([LenovoProvider], scope="function")]


@pytest.fixture(scope="module")
def physical_rack_collection(appliance, provider, setup_provider_modscope):
    # Get and return the physical rack collection
    return appliance.collections.physical_racks


def test_physical_racks_view_displayed(physical_rack_collection, provider):
    physical_racks_view = navigate_to(physical_rack_collection, 'All')
    assert physical_racks_view.is_displayed


def test_physical_racks_view_dropdowns(physical_rack_collection):
    """Navigate to the physical racks page and verify that the dropdown menus are present"""
    physical_racks_view = navigate_to(physical_rack_collection, 'All')

    configuration_items = physical_racks_view.toolbar.configuration.items
    assert "Refresh Relationships and Power States" in configuration_items
