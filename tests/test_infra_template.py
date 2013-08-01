#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestInfrastructurePXETemplate:
    def test_infrastructure_pxe_template(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        pxe_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("PXE").click()
        Assert.true(pxe_pg.is_the_current_page)

        error_text = "There should be 4 accordion items instead of %s" % len(pxe_pg.accordion_region.accordion_items)
        Assert.true(len(pxe_pg.accordion_region.accordion_items) == 4, error_text)

        pxe_pg.accordion_region.accordion_by_name("Customization Templates").click()
        pxe_pg.accordion_region.current_content.children[0].twisty.expand()
        pxe_pg.accordion_region.current_content.children[0].children[2].click()

        #This needs to be here. Configuration button is not clickable immediately.
        time.sleep(1)
        pxe_pg.center_buttons.configuration_button.click()

        #END OF PAGE TEST

        #copy_pg = pxe_pg.click_on_copy_template()
        #copy_pg.rename_template("This is a test")
        #copy_pg.select_image_type("RHEL-6")

        #This needs to be here. Add button is displayed only after a short time after selecting the image type.
        #And: 'Element must be displayed to click'
        #time.sleep(1)
        #added_pg = copy_pg.click_on_add()
        #Assert.true(added_pg.flash.message == 'Customization Template "This is a test" was added', "Flash message: %s" % added_pg.flash.message)

