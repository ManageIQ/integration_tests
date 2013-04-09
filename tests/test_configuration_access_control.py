#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestSettings:
    def test_add_new_role(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        new_role_pg = config_pg.click_on_access_control().click_on_roles().click_on_add_new()
        new_role_pg.fill_name('testrole')
        new_role_pg.select_access_restriction('user')
        show_role_pg = new_role_pg.save()
        Assert.true(show_role_pg.flash.message.startswith('Role "testrole" was saved'))

    def test_edit_role(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        edit_role_pg = config_pg.click_on_access_control().click_on_roles().click_on_role('testrole').click_on_edit()
        edit_role_pg.fill_name('testrole2')
        show_role_pg = edit_role_pg.save()
        Assert.true(show_role_pg.flash.message.startswith('Role "testrole2" was saved'))

    def test_delete_role(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        show_role_pg = config_pg.click_on_access_control().click_on_roles().click_on_role('testrole2')
        roles_pg = show_role_pg.click_on_delete()
        Assert.true(roles_pg.flash.message.startswith('Role "testrole2": Delete successful'))
