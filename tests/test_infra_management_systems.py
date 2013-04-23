#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

NAME = "test_name_2"

@pytest.mark.nondestructive #IGNORE:E1101
class TestManagementSystems:
    def test_management_systems(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        management_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()
        Assert.true(management_pg.is_the_current_page)

        new_management_system_pg = management_pg.click_on_add_new_management_system()

        new_management_system_pg.select_management_system_type("VMware vCenter")

        new_management_system_pg.new_management_system_fill_data(name = NAME)
        
        # NOTE: The rest of this test belongs in an actual functional test, not in this unit test
        # At this point, you should just read back the values that were filled in and make sure that 
        # the form was populated correctly.
        
        # ms_pg = new_management_system_pg.click_on_add()

        # flash_message = 'Management System "%s" was saved' % NAME

        # Assert.true(ms_pg.flash.message == flash_message, "Flash message is: %s" % ms_pg.flash.message)

