#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
def test_change_database_settings(home_page_logged_in):
    home_pg = home_page_logged_in
    config_pg = home_pg.header.site_navigation_menu(
            "Configuration").sub_navigation_menu("Configuration").click()
    Assert.true(config_pg.is_the_current_page)
    db_pg = config_pg.click_on_settings().\
            click_on_current_server_tree_node().click_on_database_tab()
    Assert.true(db_pg.dbtype.get_attribute('value') == 'internal')
    db_pg.set_external_postgres_db('localhost', 'none', 'none', 'none')
    db_pg.validate()
    Assert.endswith(db_pg.flash.message,
            'password authentication failed for user "none"',
            'Could not validate flash message')
    db_pg.set_external_evm_db('localhost')
    db_pg.validate()
    Assert.endswith(db_pg.flash.message,
            'validation was successful',
            'Could not validate flash message')
