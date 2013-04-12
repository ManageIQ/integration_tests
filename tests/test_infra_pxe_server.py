#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestPXEServer:
    def test_pxe_server(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        pxe_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("PXE").click()
        Assert.true(pxe_pg.is_the_current_page)

        pxe_pg.accordion_region.accordion_by_name("PXE Servers").click()
        pxe_pg.accordion_region.current_content.click()

        pxe_pg.center_buttons.configuration_button.click()
        add_pg = pxe_pg.click_on_add_pxe_server()
        add_pg.select_depot_type("Network File System")

        #This needs to be here. We need to wait until URI input is displayed.
        time.sleep(1)

        #use default values
        add_pg.new_pxe_server_fill_data(
            name = None,
            uri = None,
            access_url = None,
            pxe_dir = None,
            windows_img_dir = None,
            customization_dir = None,
            pxe_img_menus_filename = None)
        add_pg.click_on_add()

        Assert.true(add_pg.flash.message == 'PXE Server "rhel_pxe_server" was added', "Flash message: %s" % add_pg.flash.message)

