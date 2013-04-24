# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.fixture(scope="module",  # IGNORE:E1101
                params=["vsphere5"])
def management_system(request, cfme_data, mgmtsys_page):
    param = request.param
    def fin():
        # Go back to the Management Systems list
        ms_pg = mgmtsys_page.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()
        ms_pg.select_management_system(cfme_data.data["management_systems"][param]["name"])
        ms_pg.click_on_remove_management_system()
    request.addfinalizer(fin)
    return cfme_data.data["management_systems"][param]

@pytest.fixture  # IGNORE:E1101
def mgmtsys_page(home_page_logged_in):
    return home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()

@pytest.fixture  # IGNORE:E1101
def has_at_least_one_management_system(home_page_logged_in):
    ms_pg = home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()
    sleep_time = 1
    while not len(ms_pg.quadicon_region.quadicons) > 0:
        ms_pg.selenium.refresh()
        time.sleep(sleep_time)
        sleep_time *= 2

@pytest.mark.nondestructive  # IGNORE:E1101
@pytest.mark.usefixtures("maximized")  # IGNORE:E1101
class TestManagementSystems:
    def test_discover_management_systems_starts(self, mozwebqa, mgmtsys_page, management_system):
        ms_pg = mgmtsys_page
        Assert.true(ms_pg.is_the_current_page)
        msd_pg = ms_pg.click_on_discover_management_systems()
        Assert.true(msd_pg.is_the_current_page)
        ms_pg = msd_pg.discover_systems(management_system["type"], management_system["discovery_range"]["start"], management_system["discovery_range"]["end"])
        Assert.true(ms_pg.is_the_current_page)
        Assert.true(ms_pg.flash.message == "Management System: Discovery successfully initiated")

    def test_that_checks_flash_with_no_management_types_checked(self, mozwebqa, mgmtsys_page):
        ms_pg = mgmtsys_page
        Assert.true(ms_pg.is_the_current_page)
        msd_pg = ms_pg.click_on_discover_management_systems()
        msd_pg.click_on_start()
        Assert.true(msd_pg.flash.message == "At least 1 item must be selected for discovery")

    def test_that_checks_flash_when_discovery_canceled(self, mozwebqa, mgmtsys_page):
        ms_pg = mgmtsys_page
        Assert.true(ms_pg.is_the_current_page)
        msd_pg = ms_pg.click_on_discover_management_systems()
        ms_pg = msd_pg.click_on_cancel()
        Assert.true(ms_pg.is_the_current_page)
        Assert.true(ms_pg.flash.message == "Management System Discovery was cancelled by the user")

    @pytest.mark.usefixtures("has_at_least_one_management_system")  # IGNORE:E1101
    def test_edit_management_system(self, mozwebqa, mgmtsys_page, management_system):
        ms_pg = mgmtsys_page
        ms_pg.select_management_system(management_system["default_name"])
        Assert.true(len(ms_pg.quadicon_region.selected) == 1, "More than one quadicon was selected")
        mse_pg = ms_pg.click_on_edit_management_systems()
        msdetail_pg = mse_pg.edit_management_system(management_system)
        Assert.true(msdetail_pg.flash.message == "Management System \"%s\" was saved" % management_system["name"])
        Assert.true(msdetail_pg.name == management_system["name"])
        Assert.true(msdetail_pg.hostname == management_system["hostname"])
        Assert.true(msdetail_pg.zone == management_system["server_zone"])
        Assert.true(msdetail_pg.vnc_port_range == management_system["host_vnc_port"])
        # if msdetail_pg.credentials_validity == "None":
            # Try reloading the page once. If we get valid then, ok. Otherwise, failure
        #    msdetail_pg.selenium.refresh()
        # Assert.true(msdetail_pg.credentials_validity == "Valid")

