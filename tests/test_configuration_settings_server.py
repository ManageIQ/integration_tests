#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert


@pytest.mark.nondestructive
class TestConfigurationSettingsServer:
    def test_edit_server_name(self, cnf_configuration_pg):
        Assert.true(cnf_configuration_pg.is_the_current_page)
        server_pg = cnf_configuration_pg.click_on_settings()\
            .click_on_current_server_tree_node().click_on_server_tab()
        # create new name by appending to current
        temp_server_name = server_pg.get_server_name() + "-CFME"
        server_pg.set_server_name(temp_server_name)
        Assert.equal(server_pg.get_server_name(),
                     temp_server_name,
                     "Temp server name should match retrieved name")

    def test_edit_server_settings(self, cnf_configuration_pg):
        Assert.true(cnf_configuration_pg.is_the_current_page)
        server_pg = cnf_configuration_pg.click_on_settings()\
                .click_on_current_server_tree_node().click_on_server_tab()
        # select first unselected role
        role = [r for r in server_pg.server_roles if not r.is_selected][0]
        role.select()
        role_name = role.name
        server_pg.save()
        role = [r for r in server_pg.server_roles if r.name == role_name][0]
        Assert.true(role.is_selected)
        # and now unselect it again
        role.unselect()
        server_pg.save()
        role = [r for r in server_pg.server_roles if r.name == role_name][0]
        Assert.false(role.is_selected)
