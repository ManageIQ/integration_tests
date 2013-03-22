# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.fixture(scope="module",
                params=["rhevm", "virtualcenter"])
def management_system_types(request):
    return request.param

@pytest.fixture(scope="module",
                params=["192.168.0.1"])
def from_address(request):
    return request.param

@pytest.fixture(scope="module",
                params=["192.168.0.254"])
def to_address(request):
    return request.param

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestManagementSystems:
    def test_discover_management_systems_starts(self, mozwebqa, home_page_logged_in, management_system_types, from_address, to_address):
        home_pg = home_page_logged_in
        ms_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()
        Assert.true(ms_pg.is_the_current_page)
        msd_pg = ms_pg.click_on_discover_management_systems()
        Assert.true(msd_pg.is_the_current_page)
        ms_pg = msd_pg.discover_systems(management_system_types, from_address, to_address)
        Assert.true(ms_pg.is_the_current_page)
        Assert.true(ms_pg.flash.message == "Management System: Discovery successfully initiated")

#    def test_that_management_systems_discovered(self, mozwebqa):
#        # Loop until the quadicon shows up
#        pass
        
    def test_that_checks_flash_with_no_management_types_checked(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        ms_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()
        Assert.true(ms_pg.is_the_current_page)
        msd_pg = ms_pg.click_on_discover_management_systems()
        msd_pg.click_on_start()
        Assert.true(msd_pg.flash.message == "At least 1 item must be selected for discovery")
        
    def test_that_checks_flash_when_discovery_canceled(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        ms_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()
        Assert.true(ms_pg.is_the_current_page)
        msd_pg = ms_pg.click_on_discover_management_systems()
        ms_pg = msd_pg.click_on_cancel()
        Assert.true(ms_pg.is_the_current_page)
        Assert.true(ms_pg.flash.message == "Management System Discovery was cancelled by the user")
        