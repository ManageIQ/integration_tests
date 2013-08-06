#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

# pylint: disable=E1101

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestAccessControl:
    def test_add_new_role(self, cnf_configuration_pg):
        Assert.true(cnf_configuration_pg.is_the_current_page)
        new_role_pg = cnf_configuration_pg.click_on_access_control()\
                .click_on_roles().click_on_add_new()
        new_role_pg.fill_name('testrole')
        new_role_pg.select_access_restriction('user')
        show_role_pg = new_role_pg.cancel()
        Assert.contains(
            "Add of new Role was cancelled by the user",
            show_role_pg.flash.message,
            "Flash message does not match")

    def test_add_new_local_group(self, cnf_configuration_pg):
        _group_description = "test_group"
        _group_role = "EvmRole-administrator"

        Assert.true(cnf_configuration_pg.is_the_current_page)
        new_group_pg = cnf_configuration_pg.click_on_access_control()\
                .click_on_groups().click_on_add_new()
        new_group_pg.fill_info(_group_description, _group_role)
        show_group_pg = new_group_pg.cancel()
        Assert.contains(
            "Add of new Group was cancelled by the user",
            show_group_pg.flash.message,
            "Flash message does not match")

    def test_add_new_user(self, cnf_configuration_pg):
        _user_name = 'testuser'
        _user_id = 'testuser'
        _user_email = 'test@test.com'
        _user_group = 'EvmGroup-administrator'

        Assert.true(cnf_configuration_pg.is_the_current_page)
        new_user_pg = cnf_configuration_pg.click_on_access_control()\
                .click_on_users().click_on_add_new()
        new_user_pg.fill_info(
                _user_name,
                _user_id,
                _user_email,
                _user_group)
        show_user_pg = new_user_pg.click_on_cancel()
        Assert.contains(
            "Add of new User was cancelled by the user",
            show_user_pg.flash.message,
            "Flash message does not match")
