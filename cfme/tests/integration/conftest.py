import pytest

from cfme.web_ui import menu


#helper fixture used to generate a list of available navigation destinations in rbac testing
@pytest.fixture(scope='session')
def visible_pages():
    def f():
        # Gather up all the visible toplevel tabs
        menu_names = []
        toplevel_links = pytest.sel.element(menu.toplevel_tabs_loc)
        for menu_elem in pytest.sel.elements('li/a', root=toplevel_links):
            menu_names.append(pytest.sel.text(menu_elem))

        # Now go from tab to tab and pull the secondlevel names from the visible links
        displayed_menus = []
        for menu_name in menu_names:
            menu_elem = pytest.sel.element(menu.toplevel_loc % menu_name)
            pytest.sel.move_to_element(menu_elem)
            for submenu_elem in pytest.sel.elements('../ul/li/a', root=menu_elem):
                displayed_menus.append((menu_name, pytest.sel.text(submenu_elem)))

        # Do reverse lookups so we can compare to the list of nav destinations for this group
        return sorted([menu.reverse_lookup(*displayed) for displayed in displayed_menus])
    return f
