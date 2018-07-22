"""Test to validate basic navigations.Later to be replaced with End-to-End functional testing."""
import pytest

from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.ignore_stream('5.8')]


@pytest.fixture(scope="module")
def disable_migration_ui(appliance):
    appliance.disable_migration_ui()


def test_migration_ui_enable_disable(appliance, disable_migration_ui):
    appliance.enable_migration_ui()
    view = navigate_to(appliance.server, 'Dashboard', wait_for_view=True)
    nav_tree = view.navigation.nav_item_tree()
    assert 'Migration' in nav_tree['Compute'], ('Trying to find Migration in'
           ' nav_tree, should be present :{}'.format(nav_tree))
    appliance.disable_migration_ui()
    view.browser.refresh()
    view = navigate_to(appliance.server, 'Dashboard', wait_for_view=True)
    nav_tree = view.navigation.nav_item_tree()
    assert 'Migration' not in nav_tree['Compute'], ('Trying to find Migration in'
           ' nav_tree, should be absent :{}'.format(nav_tree))
