#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestConfigurationSettingsDatabase:
    def test_change_database_settings(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        db_pg = config_pg.click_on_settings().click_on_current_server_tree_node().click_on_database_tab()
        Assert.true(db_pg.dbtype.get_attribute('value') == 'internal')
        db_pg.set_external_postgres_db('localhost', 'none', 'none', 'none')
        db_pg.validate()
        Assert.true(db_pg.flash.message.endswith('"none" does not exist'))
        db_pg.set_external_evm_db('localhost')
        db_pg.validate()
        Assert.true(db_pg.flash.message.endswith('validation was successful'))
