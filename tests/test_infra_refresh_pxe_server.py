#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert
from selenium.common.exceptions import NoSuchElementException

EXPECTED_NAMES = ["rhel63server", "winpex64"]
PXE_SERVER_NAME = "rhel_pxe_server"

@pytest.mark.nondestructive
class TestInfrastructureRefreshPXEServer:
    def test_infrastructure_refresh_pxe_server(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        pxe_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("PXE").click()
        Assert.true(pxe_pg.is_the_current_page)

        pxe_pg.accordion_region.accordion_by_name("PXE Servers").click()

        children_count = len(pxe_pg.accordion_region.current_content.children)

        Assert.true(children_count > 0, "There is no PXE server")

        #TODO for now, I'm refreshing only the first PXE server in line
        pxe_pg.accordion_region.current_content.children[0].click()

        #This needs to be here. We must wait for page to refresh
        time.sleep(2)

        pxe_pg.center_buttons.configuration_button.click()

        pxe_pg.click_on_refresh()
        pxe_pg.handle_popup()

        flash_message = 'PXE Server "%s": synchronize_advertised_images_queue successfully initiated' % PXE_SERVER_NAME

        Assert.true(pxe_pg.flash.message == flash_message, "Flash message: %s" % pxe_pg.flash.message)

        for i in range(1, 8):
            try:
                #To refresh the page
                #TODO for now, I'm refreshing only the first PXE server in line
                pxe_pg.accordion_region.current_content.children[0].click()
                #This needs to be here
                time.sleep(2)
                pxe_image_names = pxe_pg.pxe_image_names()
            except NoSuchElementException:
                print("Waiting....")
                pass
            else:
                break

        for name in EXPECTED_NAMES:
            Assert.true(name in pxe_image_names, "This image has not been found: '%s'" % name)

