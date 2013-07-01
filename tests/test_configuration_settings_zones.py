#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestConfigurationSettingsZones:
    def test_add_new_zone(self, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu(
                "Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        zone_pg = config_pg.click_on_settings().click_on_zones()\
                .click_on_add_new()
        zone_pg.set_zone_info('testzone', 'zonedescription', '')
        zone_pg.set_ntp_servers('ntp1.test', '', '')
        zone_pg.set_max_scans('2')
        zones_pg = zone_pg.save()
        Assert.true(
                zones_pg.flash.message.startswith('Zone "testzone" was added'))

    def test_edit_zone(self, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu(
                "Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        zone_pg = config_pg.click_on_settings().click_on_zones()\
                .click_on_zone('Zone: zonedescription').click_on_edit()
        zone_pg.set_zone_info('zonedescription2', '')
        zone_pg.set_max_scans('3')
        zones_pg = zone_pg.save()
        Assert.true(
                zones_pg.flash.message.startswith('Zone "testzone" was saved'))

    def test_delete_zone(self, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu(
                "Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        zone_pg = config_pg.click_on_settings().click_on_zones()\
                .click_on_zone('Zone: zonedescription2')
        zone_pg.click_on_delete()
