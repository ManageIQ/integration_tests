import pytest

from pages.login import LoginPage
from utils.conf import cfme_data
from utils.browser import testsetup


def pytest_generate_tests(metafunc):
    if 'aws_iam_groups_data' in metafunc.fixturenames:
        param_group_data = []
        for group in cfme_data['group_roles']:
            param_group_data.append(['', group, cfme_data['group_roles'][group]])
        metafunc.parametrize(['aws_iam_groups_data', 'group_name', 'group_data'],
                             param_group_data, scope="module")


def validate_menus(home_pg, group_data):
    missing_items = []
    for menu in group_data["menus"]:
        assert home_pg.header.site_navigation_menu(menu).name == menu
        for item in home_pg.header.site_navigation_menu(menu).items:
            if item.name not in group_data["menus"][menu]:
                missing_items.append(item.name)
    # There should be no missing items...
    assert not missing_items


@pytest.mark.usefixtures("maximized",
                         "configure_aws_iam_auth_mode",
                         "aws_iam_groups_data")
def test_default_aws_iam_group_roles(browser, group_name, group_data):
    """Basic default AWS_IAM group role RBAC test

    Validates expected menu and submenu names are present for default
    AWS IAM groups
    """

    login_pg = LoginPage(testsetup)
    login_pg.go_to_login_page()
    if group_name not in login_pg.testsetup.credentials:
        pytest.fail("No match in credentials file for group '%s'" % group_name)
    # login as AWS IAM user
    home_pg = login_pg.login(user=group_name + '_aws_iam', force_dashboard=False)
    assert home_pg.is_logged_in, "Could not determine if logged in"
    validate_menus(home_pg, group_data)
    home_pg.header.logout()
