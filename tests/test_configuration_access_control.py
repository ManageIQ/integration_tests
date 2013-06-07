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


@pytest.mark.nondestructive
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

    def test_tag_group(self, mozwebqa, home_page_logged_in):
        _category = "Provisioning Scope"
        _value = "All"
        _group = "EvmGroup-super_administrator"
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        edit_tags_pg = config_pg.click_on_access_control().click_on_groups().click_on_group(_group).click_on_edit_tags()
        edit_tags_pg.select_category(_category)
        edit_tags_pg.select_value(_value)
        Assert.true(edit_tags_pg.is_tag_displayed(_category, _value))
        edit_tags_pg.save()
        Assert.true(edit_tags_pg.flash.message.startswith('Tag edits were successfully saved'))

    def test_delete_group_tag(self, mozwebqa, home_page_logged_in):
        _category = "Provisioning Scope"
        _value = "All"
        _group = "EvmGroup-super_administrator"
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        edit_tags_pg = config_pg.click_on_access_control().click_on_groups().click_on_group(_group).click_on_edit_tags()
        edit_tags_pg.delete_tag(_category)
        Assert.false(edit_tags_pg.is_tag_displayed(_category, _value))
        edit_tags_pg.save()
        Assert.true(edit_tags_pg.flash.message.startswith('Tag edits were successfully saved'))

    def test_cancel_tag_edit(self, mozwebqa, home_page_logged_in):
        _group = "EvmGroup-super_administrator"
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        edit_tags_pg = config_pg.click_on_access_control().click_on_groups().click_on_group(_group).click_on_edit_tags()
        edit_tags_pg.cancel()
        Assert.true(edit_tags_pg.flash.message.startswith('Tag Edit was cancelled by the user'))

    def test_reset_tag_edit(self, mozwebqa, home_page_logged_in):
        _category = "Provisioning Scope"
        _value = "All"
        _group = "EvmGroup-super_administrator"
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        edit_tags_pg = config_pg.click_on_access_control().click_on_groups().click_on_group(_group).click_on_edit_tags()
        edit_tags_pg.select_category(_category)
        edit_tags_pg.select_value(_value)
        Assert.true(edit_tags_pg.is_tag_displayed(_category, _value))
        edit_tags_pg.reset()
        Assert.false(edit_tags_pg.is_tag_displayed(_category, _value))
        Assert.true(edit_tags_pg.flash.message.startswith('All changes have been reset'))

@pytest.mark.destructive
@pytest.mark.usefixtures("maximized")
class TestUsers:
    _user_name = 'testuser'
    _user_name_edit = 'test_user_edit'
    _user_name_copy = 'test_user_copy'
    _user_id = 'testuser'
    _user_id_edit = 'test_user_edit'
    _user_id_copy = 'test_user_copy'
    _user_pswd = 'test'
    _user_email = 'test@test.com'
    _user_group = 'EvmGroup-administrator'
    def test_add_new_user(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        new_user_pg = config_pg.click_on_access_control().click_on_users().click_on_add_new()
        new_user_pg.fill_info(self._user_name, self._user_id, self._user_pswd, self._user_pswd, self._user_email, self._user_group)
        show_user_pg = new_user_pg.click_on_add()
        Assert.true(show_user_pg.flash.message.startswith('User "testuser" was saved'))

    def test_edit_user(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        edit_user_pg = config_pg.click_on_access_control().click_on_users().click_on_user(self._user_name).click_on_edit()
        edit_user_pg.fill_info(self._user_name_edit, self._user_id_edit, "", "", "", "")
        show_user_pg = edit_user_pg.click_on_save()
        Assert.true(show_user_pg.flash.message.startswith('User "test_user_edit" was saved'))

    def test_tag_user(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        edit_tags_pg = config_pg.click_on_access_control().click_on_users().click_on_user(self._user_name_edit).click_on_edit_tags()
        edit_tags_pg.select_category("Department")
        edit_tags_pg.select_value("Engineering")
        Assert.true(edit_tags_pg.is_tag_displayed("Department", "Engineering"))
        edit_tags_pg.save()
        Assert.true(edit_tags_pg.flash.message.startswith('Tag edits were successfully saved'))

    def test_delete_user_tag(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        edit_tags_pg = config_pg.click_on_access_control().click_on_users().click_on_user(self._user_name_edit).click_on_edit_tags()
        edit_tags_pg.delete_tag("Department")
        Assert.false(edit_tags_pg.is_tag_displayed("Department", "Engineering"))
        edit_tags_pg.save()
        Assert.true(edit_tags_pg.flash.message.startswith('Tag edits were successfully saved'))

    def test_cancel_tag_edits(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        edit_tags_pg = config_pg.click_on_access_control().click_on_users().click_on_user(self._user_name_edit).click_on_edit_tags()
        edit_tags_pg.cancel()
        Assert.true(edit_tags_pg.flash.message.startswith('Tag Edit was cancelled by the user'))

    def test_reset_tag_edit(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        edit_tags_pg = config_pg.click_on_access_control().click_on_users().click_on_user(self._user_name_edit).click_on_edit_tags()
        edit_tags_pg.select_category("Department")       
        edit_tags_pg.select_value("Engineering")       
        Assert.true(edit_tags_pg.is_tag_displayed("Department", "Engineering"))
        edit_tags_pg.reset()
        Assert.false(edit_tags_pg.is_tag_displayed("Department", "Engineering"))
        Assert.true(edit_tags_pg.flash.message.startswith('All changes have been reset'))

    def test_copy_user(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        copy_user_pg = config_pg.click_on_access_control().click_on_users().click_on_user(self._user_name_edit).click_on_copy()
        copy_user_pg.fill_info(self._user_name_copy, self._user_id_copy, "", "", "", "")
        show_user_pg = copy_user_pg.click_on_add()
        Assert.true(show_user_pg.flash.message.startswith('User "test_user_copy" was saved'))
        
    def test_delete_user(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        edit_user_pg = config_pg.click_on_access_control().click_on_users().click_on_user(self._user_name_edit)
        users_pg = edit_user_pg.click_on_delete()
        Assert.true(users_pg.flash.message.startswith('EVM User "test_user_edit": Delete successful'))
        edit_user_pg = users_pg.click_on_user(self._user_name_copy)
        users_pg = edit_user_pg.click_on_delete()
        Assert.true(users_pg.flash.message.startswith('EVM User "test_user_copy": Delete successful'))

        
