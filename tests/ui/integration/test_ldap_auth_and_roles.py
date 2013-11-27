#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert
from pages.login import LoginPage


@pytest.mark.parametrize('ldap_groups',
    [
        'evmgroup-administrator',
        'evmgroup-approver',
        'evmgroup-auditor',
        'evmgroup-desktop',
        'evmgroup-operator',
        'evmgroup-security',
        'evmgroup-super_administrator',
        'evmgroup-support',
        'evmgroup-user',
        'evmgroup-user_limited_self_service',
        'evmgroup-user_self_service',
        'evmgroup-vm_user'
    ]
)
@pytest.mark.usefixtures(
    'maximized', 'setup_infrastructure_providers', 'configure_auth_mode'
)
class TestLdap:
    def test_default_ldap_group_roles(self, mozwebqa, ldap_groups, cfme_data):
        """Basic default LDAP group role RBAC test

        Validates expected menu and submenu names are present for default
        LDAP group roles
        """
        if ldap_groups not in cfme_data.data['group_roles']:
            pytest.fail("No match in cfme_data for group '%s'" % ldap_groups)
        group_roles = cfme_data.data['group_roles'][ldap_groups]
        login_pg = LoginPage(mozwebqa)
        login_pg.go_to_login_page()
        if ldap_groups not in login_pg.testsetup.credentials:
            pytest.fail("No match in credentials file for group '%s'" % ldap_groups)

        # login as LDAP user
        home_pg = login_pg.login(user=ldap_groups, force_dashboard=False)
        Assert.true(home_pg.is_logged_in, 'Could not determine if logged in')

        for menu in group_roles['menus']:
            Assert.equal(home_pg.header.site_navigation_menu(menu).name, menu)
            for item in home_pg.header.site_navigation_menu(menu).items:
                Assert.contains(item.name, group_roles['menus'][menu])
