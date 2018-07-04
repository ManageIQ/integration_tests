import fauxfactory

from cfme.utils.appliance.implementations.ui import navigate_to


def test_update_help_menu(appliance):
    """Test case to check if editing items in help menu actually
    updates the help menu.
    """
    region = appliance.collections.regions.instantiate()
    updates = {'documentation_title': fauxfactory.gen_alpha()}
    view = region.set_help_menu_configuration(updates)
    view = navigate_to(appliance.server, 'Dashboard')
    view.help.click()
    assert view.help.has_item(updates['documentation_title'])
