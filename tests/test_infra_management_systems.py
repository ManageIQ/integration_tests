#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

NAME = "test_name_2"

@pytest.mark.nondestructive
class TestManagementSystems:
    def test_management_systems(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        management_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()
        Assert.true(management_pg.is_the_current_page)

        management_pg.center_buttons.configuration_button.click()
        new_management_system_pg = management_pg.click_on_add_new_management_system()

        refreshed_pg = new_management_system_pg.select_management_system_type("VMware vCenter")

        refreshed_pg.new_management_system_fill_data(
            name = NAME,
            hostname = None,
            ip_address = None,
            user_id = None,
            password = None)
        refreshed_pg.management_system_click_on_add()

        flash_message = 'Management System "%s" was saved' % NAME

        Assert.true(refreshed_pg.flash.message == flash_message, "Flash message is: %s" % refreshed_pg.flash.message)

