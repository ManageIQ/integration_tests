# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert
from selenium.common.exceptions import NoSuchElementException

@pytest.fixture(scope="module", # IGNORE:E1101
                params=["vsphere5", "rhevm31"])
def management_system(request, cfme_data):
    param = request.param
    return cfme_data.data["management_systems"][param]

@pytest.fixture(scope="module", # IGNORE:E1101
                params=["rhel"])
def pxe_server(request, cfme_data):
    param = request.param
    return cfme_data.data["pxe"]["pxe_servers"][param]

@pytest.fixture(scope="module") # IGNORE:E1101
def pxe_image_names(cfme_data):
    return cfme_data.data["pxe"]["images"]

@pytest.fixture(scope="module") # IGNORE:E1101
def pxe_datastore_names(cfme_data):
    return cfme_data.data["pxe"]["datastores"]

@pytest.fixture(scope="module", # IGNORE:E1101
                params=["rhel"])
def pxe_templates(request, cfme_data):
    param = request.param
    return cfme_data.data["pxe"]["templates"][param]

@pytest.fixture(scope="module",
                params=["rhel"]) # IGNORE:E1101
def pxe_template_type(request, cfme_data):
    param = request.param
    return cfme_data.data["pxe"]["templates"][param]["template_type"]

@pytest.fixture # IGNORE:E1101
def mgmtsys_page(home_page_logged_in):
    return home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()

@pytest.fixture # IGNORE:E1101
def pxe_page(home_page_logged_in):
    return home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("PXE").click()

@pytest.fixture # IGNORE:E1101
def has_at_least_one_management_system(home_page_logged_in):
    ms_pg = home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Management Systems").click()
    sleep_time = 1
    while not len(ms_pg.quadicon_region.quadicons) > 0:
        ms_pg.selenium.refresh()
        time.sleep(sleep_time)
        sleep_time *= 2

@pytest.mark.nondestructive # IGNORE:E1101
@pytest.mark.usefixtures("maximized", "setup_mgmt_systems") # IGNORE:E1101
class TestManagementSystems:
    def test_add_pxe_server(self, mozwebqa, pxe_page, pxe_server):
        pxe_pg = pxe_page
        Assert.true(pxe_pg.is_the_current_page)
        pxe_pg.accordion_region.accordion_by_name("PXE Servers").click()
        #click on 'All PXE Servers'
        pxe_pg.accordion_region.current_content.click()
        time.sleep(1)
        pxe_pg.center_buttons.configuration_button.click()
        add_pg = pxe_pg.click_on_add_pxe_server()
        refreshed_pg = add_pg.select_depot_type(pxe_server['depot_type'])
        refreshed_pg.new_pxe_server_fill_data(**pxe_server)
        refreshed_pg.click_on_add()
        flash_message = 'PXE Server "%s" was added' % pxe_server['name']
        Assert.true(refreshed_pg.flash.message == flash_message, "Flash message: %s" % refreshed_pg.flash.message)

    def test_refresh_pxe_server(self, mozwebqa, pxe_page, pxe_server, pxe_image_names):
        pxe_pg = pxe_page
        Assert.true(pxe_pg.is_the_current_page)
        pxe_pg.accordion_region.accordion_by_name("PXE Servers").click()
        children_count = len(pxe_pg.accordion_region.current_content.children)
        Assert.true(children_count > 0, "There is no PXE server")
        pxe_pg.accordion_region.current_content.find_node_by_name(pxe_server['name']).click()
        #This needs to be here. We must wait for page to refresh
        time.sleep(2)
        pxe_pg.center_buttons.configuration_button.click()
        pxe_pg.click_on_refresh()
        pxe_pg.handle_popup()
        flash_message = 'PXE Server "%s": synchronize_advertised_images_queue successfully initiated' % pxe_server['name']
        Assert.true(pxe_pg.flash.message == flash_message, "Flash message: %s" % pxe_pg.flash.message)

        pxe_image_names_from_page = -1

        for i in range(1, 8):
            try:
                #To refresh the page
                pxe_pg.accordion_region.current_content.find_node_by_name(pxe_server['name']).click()
                #This needs to be here
                time.sleep(2)
                pxe_image_names_from_page = pxe_pg.pxe_image_names()
            except NoSuchElementException:
                print("Waiting.... %s" % i)
                pass
            else:
                break

        Assert.false(pxe_image_names_from_page == -1, "Could not assert for expected names.")

        for name in pxe_image_names:
            Assert.true(name in pxe_image_names_from_page, "This image has not been found: '%s'" % name)

    def test_add_customization_template(self, mozwebqa, pxe_page, pxe_templates, pxe_template_type):
        pxe_pg = pxe_page
        Assert.true(pxe_pg.is_the_current_page)
        error_text = "There should be 4 accordion items instead of %s" % len(pxe_pg.accordion_region.accordion_items)
        Assert.true(len(pxe_pg.accordion_region.accordion_items) == 4, error_text)
        pxe_pg.accordion_region.accordion_by_name("Customization Templates").click()
        pxe_pg.center_buttons.configuration_button.click()
        add_pg = pxe_pg.click_on_add_template()
        temp_pg = add_pg.new_pxe_template_select_type(pxe_template_type)
        temp_pg.new_pxe_template_fill_data(**pxe_templates)
        #This needs to be here. Add button is displayed only after a short time after selecting the image type.
        #And: 'Element must be displayed to click'
        time.sleep(1)
        added_pg = temp_pg.click_on_add()
        flash_message = 'Customization Template "%s" was added' % pxe_templates["name"]
        Assert.true(added_pg.flash.message == flash_message, "Flash message: %s" % added_pg.flash.message)

    def test_iso_datastores(self, mozwebqa, pxe_page, pxe_datastore_names):
        pxe_pg = pxe_page
        Assert.true(pxe_pg.is_the_current_page)
        pxe_pg.accordion_region.accordion_by_name("ISO Datastores").click()
        pxe_pg.accordion_region.current_content.click()
        time.sleep(1)
        for name in pxe_datastore_names:
            pxe_pg.center_buttons.configuration_button.click()
            add_pg = pxe_pg.click_on_add_iso_datastore()
            add_pg.select_management_system(name)
            time.sleep(2)
            result_pg = add_pg.click_on_add()
            flash_message = 'ISO Datastore "%s" was added' %name
            Assert.true(result_pg.flash.message == flash_message, "Flash message: %s" % result_pg.flash.message)
            datastore_name = result_pg.datastore_name()
            Assert.true(name == datastore_name, "Actual name of datastore is: %s" % datastore_name)
