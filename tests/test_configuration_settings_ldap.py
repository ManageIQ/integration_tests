#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert


@pytest.mark.usefixtures("maximized")
@pytest.mark.nondestructive
class TestSettings:
    def test_configure_ldap(self, mozwebqa, home_page_logged_in):
        _ldap_settings = {"hostname1": "ad.server.example.com",
                          "user_suffix": "ad.server.example.com",
                          "base_dn": "dc=ad,dc=server,dc=example,dc=com",
                          "bind_dn": "administrator@ad.server.example.com",
                          "bind_passwd": "password"
                          }
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        auth_pg = config_pg.click_on_settings().click_on_current_server_tree_node().click_on_authentication_tab()
        Assert.true(auth_pg.is_the_current_page)
        auth_pg.ldap_server_fill_data(**_ldap_settings)
        auth_pg = auth_pg.reset()
        Assert.true(auth_pg.flash.message == "All changes have been reset")
