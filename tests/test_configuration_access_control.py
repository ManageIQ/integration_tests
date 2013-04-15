#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestRoles:
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


@pytest.mark.destructive
@pytest.mark.usefixtures("maximized")
class TestGroups:
    _group_description = "test_group"
    _group_description_edit = "test_group_edit"
    _group_role = "EvmRole-administrator"
    _group_role_edit = "EvmRole-user"

    def test_add_new_local_group(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        new_group_pg = config_pg.click_on_access_control().click_on_groups().click_on_add_new()
        new_group_pg.fill_info(self._group_description, self._group_role)
        show_group_pg = new_group_pg.save()
        Assert.true(show_group_pg.flash.message.startswith('Group "%s" was saved' % self._group_description))

    def test_edit_group(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        edit_group_pg = config_pg.click_on_access_control().click_on_groups().click_on_group(self._group_description).click_on_edit()
        edit_group_pg.fill_info(self._group_description_edit, self._group_role_edit)
        show_group_pg = edit_group_pg.save()
        Assert.true(show_group_pg.flash.message.startswith('Group "%s" was saved' % self._group_description_edit))

    def test_delete_group(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        show_group_pg = config_pg.click_on_access_control().click_on_groups().click_on_group(self._group_description_edit)
        show_group_pg = show_group_pg.click_on_delete()
        Assert.true(show_group_pg.flash.message.startswith('EVM Group "%s": Delete successful' % self._group_description_edit))
