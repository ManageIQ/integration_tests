import pytest

from cfme.fixtures import pytest_selenium as sel
from cfme.login import force_login_user, logout
from cfme.web_ui import menu
from utils.conf import cfme_data, credentials


def pytest_generate_tests(metafunc):
    for auth_fixture_type_name in ('ldap_groups_data', 'aws_iam_groups_data'):
        if auth_fixture_type_name in metafunc.fixturenames:
            param_group_data = []
            param_group_ids = []
            for group in cfme_data['group_roles']:
                param_group_data.append(['', group, cfme_data['group_roles'][group]])
                param_group_ids.append(group)
            metafunc.parametrize([auth_fixture_type_name, 'group_name', 'group_data'],
                                 param_group_data, ids=param_group_ids, scope="function")


def validate_menus(group_name, group_data):
    # Gather up all the visible toplevel tabs
    menu_names = []
    toplevel_links = sel.element(menu.toplevel_tabs_loc)
    for menu_elem in sel.elements('li/a', root=toplevel_links):
        menu_names.append(sel.text(menu_elem))

    # Now go from tab to tab and pull the secondlevel names from the visible links
    displayed_menus = []
    for menu_name in menu_names:
        menu_elem = sel.element(menu.toplevel_loc % menu_name)
        sel.move_to_element(menu_elem)
        for submenu_elem in sel.elements('../ul/li/a', root=menu_elem):
            displayed_menus.append((menu_name, sel.text(submenu_elem)))

    # Do reverse lookups so we can compare to the list of nav destinations for this group
    displayed_dests = [menu.reverse_lookup(*displayed_menu) for displayed_menu in displayed_menus]

    # Compare them
    assert sorted(displayed_dests) == sorted(group_data)


@pytest.mark.usefixtures("maximized",
                         "configure_ldap_auth_mode",
                         "ldap_groups_data")
def test_default_ldap_group_roles(browser, group_name, group_data):
    """Basic default LDAP group role RBAC test

    Validates expected menu and submenu names are present for default
    LDAP group roles
    """
    if group_name not in credentials:
        pytest.fail("No match in credentials file for group '%s'" % group_name)
    username = credentials[group_name]['username']
    password = credentials[group_name]['password']
    force_login_user(username, password)
    validate_menus(group_name, group_data)
    logout()


@pytest.mark.usefixtures("maximized",
                         "configure_aws_iam_auth_mode",
                         "aws_iam_groups_data")
def test_default_aws_iam_group_roles(browser, group_name, group_data):
    """Basic default AWS_IAM group role RBAC test

    Validates expected menu and submenu names are present for default
    AWS IAM groups
    """
    if group_name not in credentials:
        pytest.fail("No match in credentials file for group '%s'" % group_name)
    username = credentials[group_name + '_aws_iam']['username']
    password = credentials[group_name + '_aws_iam']['password']
    force_login_user(username, password)
    validate_menus(group_name, group_data)
    logout()
