#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert
from pages.login import LoginPage
from utils.cfme_data import load_cfme_data


def pytest_generate_tests(metafunc):
    if 'ldap_groups_data' in metafunc.fixturenames:
        param_group_data = []
        data = load_cfme_data(metafunc.config.option.cfme_data_filename)
        for group in data['group_roles']:
            param_group_data.append(['', group, data['group_roles'][group]])
        metafunc.parametrize(['ldap_groups_data', 'group_name', 'group_data'],
                             param_group_data, scope="module")


def validate_menus(home_pg, group_roles, ldap_group):
    for menu in group_roles["menus"]:
        Assert.equal(home_pg.header.site_navigation_menu(menu).name, menu)
        for item in home_pg.header.site_navigation_menu(menu).items:
            Assert.contains(item.name, group_roles["menus"][menu],
                            "LDAP group %s doesn't contain %s in roles" % (ldap_group, item.name))


@pytest.mark.usefixtures("maximized",
                         "configure_auth_mode",
                         "ldap_groups_data")
def test_default_ldap_group_roles(mozwebqa, group_name, group_data):
    """Basic default LDAP group role RBAC test

    Validates expected menu and submenu names are present for default
    LDAP group roles
    """

    login_pg = LoginPage(mozwebqa)
    login_pg.go_to_login_page()
    if group_name not in login_pg.testsetup.credentials:
        pytest.fail("No match in credentials file for group '%s'" % group_name)
    # login as LDAP user
    home_pg = login_pg.login(user=group_name, force_dashboard=False)
    Assert.true(home_pg.is_logged_in, "Could not determine if logged in")
    validate_menus(home_pg, group_data, group_name)


def test_auth_set_to_database(cnf_configuration_pg):
    """Sets auth mode to internal

    This test tests setting the auth_mode back to database, it also serves as cleanup
    to the above test, test_default_ldap_group_roles()
    """

    auth_pg = cnf_configuration_pg.click_on_settings()\
                                  .click_on_current_server_tree_node().click_on_authentication_tab()
    auth_pg.select_dropdown_by_value('database', *auth_pg._auth_mode_selector)
    auth_pg = auth_pg.save()
