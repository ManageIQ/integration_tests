# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert
from selenium.common.exceptions import NoSuchElementException

#CONSTANTS
#expected name of datastore - test_iso_datastores
#also name of a management system
EXPECTED_DATASTORE_NAME = "RHEV-M (10.16.120.71)"
#expected names of images - test_infrastructure_refresh_pxe_server
EXPECTED_PXE_IMAGE_NAMES = ["rhel63server", "winpex64"]
#name of pxe server - test_infrastructure_refresh_pxe_server
#and - test_pxe_server
PXE_SERVER_NAME = "rhel_pxe_server"
#name of copied template - test_infrastructure_pxe_template
TEMPLATE_NAME = "This is a test"

@pytest.fixture  # IGNORE:E1101
def pxe_page(home_page_logged_in):
    return home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("PXE").click()

def wait_for_image_names(pxe_pg, number_of_tries = 8):
    pxe_image_names = -1

    for i in range(1, number_of_tries):
        try:
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

    Assert.false(pxe_image_names == -1, "Could not assert for expected names.")
    return pxe_image_names

@pytest.mark.nondestructive  # IGNORE:E1101
class TestPXE:
    def test_pxe_server(self, mozwebqa, home_page_logged_in):
        pxe_pg = pxe_page(home_page_logged_in)
        Assert.true(pxe_pg.is_the_current_page)
        pxe_pg.accordion_region.accordion_by_name("PXE Servers").click()
        pxe_pg.accordion_region.current_content.click()
        time.sleep(1)
        pxe_pg.center_buttons.configuration_button.click()
        add_pg = pxe_pg.click_on_add_pxe_server()
        refreshed_pg = add_pg.select_depot_type("Network File System")
        #use default values (except the name)
        refreshed_pg.new_pxe_server_fill_data(name=PXE_SERVER_NAME)
        refreshed_pg.click_on_add()
        flash_message = 'PXE Server "%s" was added' % PXE_SERVER_NAME
        Assert.true(refreshed_pg.flash.message == flash_message, "Flash message: %s" % refreshed_pg.flash.message)

    def test_infrastructure_refresh_pxe_server(self, mozwebqa, home_page_logged_in):
        pxe_pg = pxe_page(home_page_logged_in)
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
        image_names = wait_for_image_names(pxe_pg)

        for name in EXPECTED_PXE_IMAGE_NAMES:
            Assert.true(name in image_names, "This image has not been found: '%s'" % name)

    def test_iso_datastores(self, mozwebqa, home_page_logged_in):
        pxe_pg = pxe_page(home_page_logged_in)
        Assert.true(pxe_pg.is_the_current_page)
        pxe_pg.accordion_region.accordion_by_name("ISO Datastores").click()
        pxe_pg.accordion_region.current_content.click()
        time.sleep(1)
        pxe_pg.center_buttons.configuration_button.click()
        add_pg = pxe_pg.click_on_add_iso_datastore()
        add_pg.select_management_system(EXPECTED_DATASTORE_NAME)
        time.sleep(2)
        result_pg = add_pg.click_on_add()
        flash_message = 'ISO Datastore "%s" was added' % EXPECTED_DATASTORE_NAME
        Assert.true(result_pg.flash.message == flash_message, "Flash message: %s" % result_pg.flash.message)
        datastore_name = result_pg.datastore_name()
        Assert.true(EXPECTED_DATASTORE_NAME == datastore_name, "Actual name of datastore is: %s" % datastore_name)

    def test_infrastructure_pxe_template(self, mozwebqa, home_page_logged_in):
        pxe_pg = pxe_page(home_page_logged_in)
        Assert.true(pxe_pg.is_the_current_page)
        error_text = "There should be 4 accordion items instead of %s" % len(pxe_pg.accordion_region.accordion_items)
        Assert.true(len(pxe_pg.accordion_region.accordion_items) == 4, error_text)
        pxe_pg.accordion_region.accordion_by_name("Customization Templates").click()
        pxe_pg.accordion_region.current_content.children[0].twisty.expand()
        pxe_pg.accordion_region.current_content.children[0].children[2].click()
        #This needs to be here. Configuration button is not clickable immediately.
        time.sleep(1)
        pxe_pg.center_buttons.configuration_button.click()
        copy_pg = pxe_pg.click_on_copy_template()
        copy_pg.rename_template(TEMPLATE_NAME)
        copy_pg.select_image_type("RHEL-6")
        #This needs to be here. Add button is displayed only after a short time after selecting the image type.
        #And: 'Element must be displayed to click'
        time.sleep(1)
        added_pg = copy_pg.click_on_add()
        Assert.true(added_pg.flash.message == 'Customization Template "%s" was added' % TEMPLATE_NAME, "Flash message: %s" % added_pg.flash.message)
