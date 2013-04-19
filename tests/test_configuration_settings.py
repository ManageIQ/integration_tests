#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestConfigurationSettings:
    def test_edit_server_settings(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        server_pg = config_pg.click_on_settings().click_on_current_server_tree_node().click_on_server_tab()
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
