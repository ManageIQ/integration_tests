#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert


@pytest.mark.usefixtures("maximized")
@pytest.mark.nondestructive
class TestSettings:
    def test_configure_ldap(self, cnf_configuration_pg):
        _ldap_settings = {"hostname1": "ad.server.example.com",
                          "user_suffix": "ad.server.example.com",
                          "base_dn": "dc=ad,dc=server,dc=example,dc=com",
                          "bind_dn": "administrator@ad.server.example.com",
                          "bind_passwd": "password"
                          }
        auth_pg = cnf_configuration_pg.click_on_settings()\
                .click_on_current_server_tree_node()\
                .click_on_authentication_tab()
        Assert.true(auth_pg.is_the_current_page)
        auth_pg.ldap_server_fill_data(**_ldap_settings)
        auth_pg = auth_pg.reset()
        Assert.equal(auth_pg.flash.message, "All changes have been reset")
