import pytest

from cfme.exceptions import CFMEException
from cfme.fixtures import pytest_selenium as sel
from cfme.login import force_login_user, logout
from utils.conf import cfme_data, credentials


def menu_by_name(menu_name):
    import cfme.web_ui.menu
    try:
        return getattr(cfme.web_ui.menu, menu_name)
    except KeyError:
        raise CFMEException("There is no '{}' menu defined in cfme.web_ui.menu module"
                            .format(menu_name))


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
    displayed_menus = {}
    navbar = menu_by_name('main')

    # Save menus that are available to the user and sort them
    for menu_name, menu_loc in navbar.locators.iteritems():
        if sel.is_displayed(menu_loc):
            displayed_menus[menu_name] = []
            sel.move_to_element(menu_loc)
            menu = menu_by_name(menu_name)
            for submenu_name, submenu_loc in menu.locators.iteritems():
                if sel.is_displayed(submenu_loc):
                    displayed_menus[menu_name].append(submenu_name)
            displayed_menus[menu_name].sort()

    # Sort the yaml menus
    for menu_name in group_data["menus"]:
        group_data["menus"][menu_name].sort()

    # Compare them
    assert displayed_menus == group_data["menus"]


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
