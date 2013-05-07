#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert
from pages.login import LoginPage

@pytest.fixture(scope="module", # IGNORE:E1101
                params=["vsphere5", "rhevm31"])
def management_system(request, cfme_data):
    param = request.param
    return cfme_data.data["management_systems"][param]

@pytest.fixture # IGNORE:E1101
def mgmtsys_page(home_page_logged_in):
    return home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()

@pytest.fixture # IGNORE:E1101
def has_at_least_one_management_system(home_page_logged_in):
    ms_pg = home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()
    sleep_time = 1
    while not len(ms_pg.quadicon_region.quadicons) > 0:
        ms_pg.selenium.refresh()
        time.sleep(sleep_time)
        sleep_time *= 2

@pytest.mark.nondestructive # IGNORE:E1101
@pytest.mark.usefixtures("maximized") # IGNORE:E1101
class TestManagementSystems:
    def test_discover_management_systems_starts(self, mozwebqa, mgmtsys_page, management_system):
        ms_pg = mgmtsys_page
        Assert.true(ms_pg.is_the_current_page)
        msd_pg = ms_pg.click_on_discover_management_systems()
        Assert.true(msd_pg.is_the_current_page)
        ms_pg = msd_pg.discover_systems(management_system["type"], management_system["discovery_range"]["start"], management_system["discovery_range"]["end"])
        Assert.true(ms_pg.is_the_current_page)
        Assert.true(ms_pg.flash.message == "Management System: Discovery successfully initiated")

    @pytest.mark.usefixtures("has_at_least_one_management_system") #IGNORE:E1101
    def test_edit_management_system(self, mozwebqa, mgmtsys_page, management_system):
        ms_pg = mgmtsys_page
        ms_pg.select_management_system(management_system["default_name"])
        Assert.true(len(ms_pg.quadicon_region.selected) == 1, "More than one quadicon was selected")
        mse_pg = ms_pg.click_on_edit_management_systems()
        msdetail_pg = mse_pg.edit_management_system(management_system)
        Assert.true(msdetail_pg.flash.message == "Management System \"%s\" was saved" % management_system["name"])
        Assert.true(msdetail_pg.name == management_system["name"])
        Assert.true(msdetail_pg.hostname == management_system["hostname"])
        Assert.true(msdetail_pg.zone == management_system["server_zone"])
        if "host_vnc_port" in management_system:
            Assert.true(msdetail_pg.vnc_port_range == management_system["host_vnc_port"])

@pytest.mark.usefixtures("maximized")
@pytest.mark.nondestructive  # IGNORE:E1101
@pytest.mark.parametrize("ldap_groups", [
    "evmgroup-administrator",
    "evmgroup-approver",
    "evmgroup-auditor",
    "evmgroup-desktop",
    "evmgroup-operator",
    "evmgroup-security",
    "evmgroup-super_administrator",
    "evmgroup-support",
    "evmgroup-user",
    "evmgroup-user_limited_self_service",
    "evmgroup-user_self_service",
    "evmgroup-vm_user" ])
class TestLdap:
    def test_default_ldap_group_roles(self, mozwebqa, ldap_groups, cfme_data):
        """Basic default LDAP group role RBAC test
        
        Validates expected menu and submenu names are present for default 
        LDAP group roles
        """
        if ldap_groups not in cfme_data.data['group_roles']:
            pytest.xfail("No match in cfme_data for group '%s'" % ldap_groups)
        _group_roles = cfme_data.data['group_roles'][ldap_groups]
        login_pg = LoginPage(mozwebqa)
        login_pg.go_to_login_page()
        if ldap_groups not in login_pg.testsetup.credentials:
            pytest.xfail("No match in credentials file for group '%s'" % ldap_groups)
        # login as LDAP user
        home_pg = login_pg.login(user=ldap_groups)
        Assert.true(home_pg.is_logged_in, "Could not determine if logged in")
        for menu in _group_roles["menus"]:
            Assert.true(home_pg.header.site_navigation_menu(menu).name == menu)
            for item in home_pg.header.site_navigation_menu(menu).items:
                Assert.true(item.name in _group_roles["menus"][menu])
        # TODO: click through submenu pages, assert is_the_current_page

