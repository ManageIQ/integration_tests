# -*- coding: utf-8 -*-
# pylint: disable=E1101
import pytest
import time
from unittestzero import Assert
from selenium.common.exceptions import NoSuchElementException

@pytest.fixture(scope="module", # IGNORE:E1101
                params=["rhel"])
def pxe_server(request, cfme_data):
    param = request.param
    return cfme_data["pxe"]["pxe_servers"][param]

@pytest.fixture(scope="module")
def pxe_image_names(cfme_data):
    return cfme_data["pxe"]["images"]

@pytest.fixture(scope="module")
def pxe_datastore_names(cfme_data):
    return cfme_data["pxe"]["datastores"]

@pytest.fixture(scope="module",
                params=["rhel"])
def pxe_templates(request, cfme_data):
    param = request.param
    return cfme_data["pxe"]["templates"][param]

@pytest.fixture(scope="module",
                params=["rhel"])
def pxe_template_type(request, cfme_data):
    param = request.param
    return cfme_data["pxe"]["templates"][param]["template_type"]

FLASH_MESSAGE_NOT_MATCHED = 'Flash message not matched'

@pytest.mark.nondestructive # IGNORE:E1101
@pytest.mark.usefixtures("maximized", "setup_infrastructure_providers")
class TestPxeSetup:
    def test_add_pxe_server(self, infra_pxe_pg, pxe_server):
        Assert.true(infra_pxe_pg.is_the_current_page)
        infra_pxe_pg.accordion_region.accordion_by_name("PXE Servers").click()
        #click on 'All PXE Servers'
        infra_pxe_pg.accordion_region.current_content.click()
        time.sleep(1)
        infra_pxe_pg.center_buttons.configuration_button.click()
        add_pg = infra_pxe_pg.click_on_add_pxe_server()
        refreshed_pg = add_pg.select_depot_type(pxe_server['depot_type'])
        refreshed_pg.new_pxe_server_fill_data(**pxe_server)
        refreshed_pg.click_on_add()
        flash_message = 'PXE Server "%s" was added' % pxe_server['name']
        Assert.equal(refreshed_pg.flash.message, flash_message,
                FLASH_MESSAGE_NOT_MATCHED)

    def test_refresh_pxe_server(
                self,
                infra_pxe_pg,
                pxe_server,
                pxe_image_names):
        Assert.true(infra_pxe_pg.is_the_current_page)
        infra_pxe_pg.accordion_region.accordion_by_name("PXE Servers").click()
        children_count = len(
                infra_pxe_pg.accordion_region.current_content.children)
        Assert.true(children_count > 0, "There is no PXE server")
        infra_pxe_pg.accordion_region.current_content.find_node_by_name(
                pxe_server['name']).click()
        #This needs to be here. We must wait for page to refresh
        time.sleep(2)
        infra_pxe_pg.center_buttons.configuration_button.click()
        infra_pxe_pg.click_on_refresh()
        infra_pxe_pg.handle_popup()
        flash_message = 'PXE Server "%s": synchronize_advertised_images_queue successfully initiated' % pxe_server['name']
        Assert.equal(infra_pxe_pg.flash.message, flash_message,
                FLASH_MESSAGE_NOT_MATCHED)

        pxe_image_names_from_page = -1

        for i in range(1, 8):
            try:
                #To refresh the page
                infra_pxe_pg.accordion_region.current_content.find_node_by_name(
                        pxe_server['name']).click()
                #This needs to be here
                time.sleep(2)
                pxe_image_names_from_page = infra_pxe_pg.pxe_image_names()
            except NoSuchElementException:
                print("Waiting.... %s" % i)
                pass
            else:
                break

        Assert.not_equal(pxe_image_names_from_page, -1,
                "Could not assert for expected names.")

        for name in pxe_image_names:
            Assert.true(name in pxe_image_names_from_page,
                    "This image has not been found: '%s'" % name)

    def test_add_customization_template(
            self,
            infra_pxe_pg,
            pxe_templates,
            pxe_template_type):
        Assert.true(infra_pxe_pg.is_the_current_page)
        error_text = "There should be 4 accordion items instead of %s" % len(
                infra_pxe_pg.accordion_region.accordion_items)
        Assert.equal(len(infra_pxe_pg.accordion_region.accordion_items), 4,
                error_text)
        infra_pxe_pg.accordion_region.accordion_by_name(
                "Customization Templates").click()
        infra_pxe_pg.center_buttons.configuration_button.click()
        add_pg = infra_pxe_pg.click_on_add_template()
        temp_pg = add_pg.new_pxe_template_select_type(pxe_template_type)
        temp_pg.new_pxe_template_fill_data(**pxe_templates)
        #This needs to be here. Add button is displayed only after a short time
        #after selecting the image type.
        #And: 'Element must be displayed to click'
        time.sleep(1)
        added_pg = temp_pg.click_on_add()
        flash_message = 'Customization Template "%s" was added' % pxe_templates["name"]
        Assert.equal(added_pg.flash.message, flash_message,
                FLASH_MESSAGE_NOT_MATCHED)

    def test_iso_datastores(self, infra_pxe_pg, pxe_datastore_names):
        Assert.true(infra_pxe_pg.is_the_current_page)
        infra_pxe_pg.accordion_region.accordion_by_name(
                "ISO Datastores").click()
        infra_pxe_pg.accordion_region.current_content.click()
        time.sleep(1)
        for name in pxe_datastore_names:
            infra_pxe_pg.center_buttons.configuration_button.click()
            add_pg = infra_pxe_pg.click_on_add_iso_datastore()
            add_pg.select_provider(name)
            time.sleep(2)
            result_pg = add_pg.click_on_add()
            flash_message = 'ISO Datastore "%s" was added' %name
            Assert.equal(result_pg.flash.message, flash_message,
                    FLASH_MESSAGE_NOT_MATCHED)
            datastore_name = result_pg.datastore_name()
            Assert.equal(name, datastore_name,
                    'Datastore name not equal')
