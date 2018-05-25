"""Test to validate basic navigations.Later to be replaced with End-to-End functional testing."""
import pytest

from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.ignore_stream('5.8', '5.9')]


@pytest.mark.tier(0)
def test_compute_migration_modal(appliance):
    """Test takes an appliance and tries to navigate to migration page and open mapping wizard.

    This is a dummy test just to check navigation.
    # TODO : Replace this test with actual test.
    """
    infra_mapping_collection = appliance.collections.v2v_mappings
    view = navigate_to(infra_mapping_collection, 'All')
    assert view.is_displayed
    view = navigate_to(infra_mapping_collection, 'Add')
    assert view.is_displayed
