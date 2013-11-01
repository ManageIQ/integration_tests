'''
@author: psavage
'''
# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621

import pytest
from unittestzero import Assert

SVR_NAME_MISMATCH = "Server Name should match value in Settings Page"


@pytest.mark.destructive
def test_server_name(cnf_configuration_pg):
    '''Tests that changing the server name updates the about page'''
    settings = cnf_configuration_pg.click_on_settings()
    server_settings = settings.click_on_current_server_tree_node()
    server_settings_tab = server_settings.click_on_server_tab()
    temp_server_name = server_settings_tab.get_server_name()
    new_server_name = temp_server_name + "-CFME"
    server_settings_tab.set_server_name(new_server_name)
    server_settings_tab.save()
    pg_flash_msg = cnf_configuration_pg.flash.message
    flash_msg = "Configuration settings saved for CFME Server \"" + \
                new_server_name
    Assert.contains(flash_msg, pg_flash_msg,
                    "Flashed message not matched")
    about_pg = cnf_configuration_pg.header. \
        site_navigation_menu('Configure'). \
        sub_navigation_menu('About').click()
    Assert.equal(new_server_name, about_pg.server_name, SVR_NAME_MISMATCH)
    about_pg.header.site_navigation_menu('Configure'). \
        sub_navigation_menu('Configuration').click()
    server_settings = settings.click_on_current_server_tree_node()
    server_settings_tab = server_settings.click_on_server_tab()
    server_settings_tab.set_server_name(temp_server_name)
    server_settings_tab.save()
