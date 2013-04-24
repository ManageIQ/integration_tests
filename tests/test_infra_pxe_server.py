#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

NAME = "rhel_pxe_server"

@pytest.mark.nondestructive  # IGNORE:E1101
class TestPXEServer:
    def test_pxe_server(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        pxe_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("PXE").click()
        Assert.true(pxe_pg.is_the_current_page)

        pxe_pg.accordion_region.accordion_by_name("PXE Servers").click()
        pxe_pg.accordion_region.current_content.click()

        pxe_pg.center_buttons.configuration_button.click()
        add_pg = pxe_pg.click_on_add_pxe_server()
        refreshed_pg = add_pg.select_depot_type("Network File System")

        #use default values
        refreshed_pg.new_pxe_server_fill_data(name=NAME)
        refreshed_pg.click_on_add()

        flash_message = 'PXE Server "%s" was added' % NAME

        Assert.true(refreshed_pg.flash.message == flash_message, "Flash message: %s" % refreshed_pg.flash.message)

