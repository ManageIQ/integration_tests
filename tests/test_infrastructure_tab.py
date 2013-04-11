#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
class TestInfrastructureTab:
    def test_infrastructure_tab(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        #Assert.true(home_pg.is_logged_in, "Could not determine if logged in")

        #infra_pg = home_pg.header.site_navigation_menu("Infrastructure").click()
        #Assert.true(infra_pg.is_the_current_page)

        pxe_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("PXE").click()
        Assert.true(pxe_pg.is_the_current_page)

        error_text = "There should be 4 accordion items instead of %s" % len(pxe_pg.accordion_region.accordion_items)
        Assert.true(len(pxe_pg.accordion_region.accordion_items) == 4, error_text)

        #pxe_pg.accordion_region.accordion_items[3].click()

        pxe_pg.accordion_region.accordion_by_name("Customization Templates").click()

        #content = pxe_pg.accordion_region.current_content
        #pxe_pg.accordion_region.current_content.children[0].click()

        #Assert.true(3 == 2, pxe_pg.accordion_region.current_content.children[0].twisty._twisty_state)
        pxe_pg.accordion_region.current_content.children[0].twisty.expand()
        #Assert.true(3 == 2, pxe_pg.accordion_region.current_content.children[0].twisty._twisty_state)
        #pxe_pg.accordion_region.current_content.children[0].children[2].click_on_server_pxe()
        pxe_pg.accordion_region.current_content.children[0].children[2].click()


        #pxe_pg.center_buttons().configuration_button.click()
        #pxe_pg.center_buttons()

        #history = pxe_pg.history_buttons()
        #history.refresh_button.click()

        time.sleep(1)

        #pxe_pg.history_buttons.refresh_button.click()
        pxe_pg.center_buttons.configuration_button.click()

        time.sleep(1)

        pxe_pg.center_buttons.configuration_button_copy.click()

        #Assert.true(3 == 2, config)

