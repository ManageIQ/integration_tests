'''
Created on July 25th, 2013

@author: Shveta
'''

import pytest
from unittestzero import Assert

@pytest.fixture(scope="module", # IGNORE:E1101
                params=["linux_template_workflow"])
def provisioning_data(request, cfme_data):
    '''get data from cfme_data.yml'''
    param = request.param
    return cfme_data.data["provisioning"][param]


@pytest.fixture()
def create_service_dialog(
        automate_customization_pg,
        random_string,
        provisioning_data):
    '''Fixture to create Catalog item and bundle'''
    new_dialog_pg = automate_customization_pg\
            .click_on_service_dialog_accordion().add_new_service_dialog()
    service_dialog_name = "auto_dialog_" + random_string
    new_dialog_pg.create_service_dialog(service_dialog_name)
    return service_dialog_name

@pytest.fixture()
def create_catalog(svc_catalogs_pg, random_string, provisioning_data):
    '''Fixture to create Catalog item and bundle'''
    new_cat_pg = svc_catalogs_pg.click_on_catalogs_accordion().add_new_catalog()
    catalog_name = "auto_cat_" + random_string
    new_cat_pg.fill_basic_info_tab(catalog_name)
    return catalog_name

@pytest.fixture()
def create_catalog_item(
        svc_catalogs_pg,
        random_string,
        provisioning_data,
        create_service_dialog,
        create_catalog):
    '''Fixture to create Catalog item and bundle'''
    service_dialog_name = create_service_dialog
    catalog_name = create_catalog
    new_cat_item_pg = svc_catalogs_pg.click_on_catalog_item_accordion().\
            add_new_catalog_item()
    new_cat_item_pg.choose_catalog_item_type('VMware')
    catalog_item_name = "auto_item_" + random_string
    new_cat_item_pg.fill_basic_info(
            catalog_item_name,
            "item_desc_" + random_string,
            catalog_name,
            service_dialog_name,
            "2")
    req_pg = new_cat_item_pg.click_on_request_info_tab()
    req_pg.fill_catalog_tab(
            provisioning_data["template"],
            "vm_name" + random_string)
    envt_pg = req_pg.click_on_environment_tab()
    item_pg = envt_pg.fill_environment_tab(
            unicode(provisioning_data["host"]),
            unicode(provisioning_data["datastore"]))
    names = [service_dialog_name, catalog_name, catalog_item_name]
    return names

@pytest.fixture()
def create_catalog_bundle(
        svc_catalogs_pg,
        random_string,
        provisioning_data,
        create_catalog_item):
    '''Fixture to create Catalog item and bundle'''
    cat_list = create_catalog_item
    cat_name = cat_list[1]
    new_bundle_pg = svc_catalogs_pg.click_on_catalog_item_accordion()\
            .add_new_catalog_bundle()
    catalog_bundle_name = "auto_bundle_" + random_string
    new_bundle_pg.fill_bundle_basic_info(
            catalog_bundle_name,
            "bundle_desc_" + random_string,
            cat_list[1],
            cat_list[0],
            "2")
    res_pg = new_bundle_pg.click_on_resources_tab()
    res_pg.select_catalog_item(cat_list[2])
    item_names = [cat_name, catalog_bundle_name]
    return item_names


@pytest.mark.nondestructive
@pytest.mark.usefixtures("create_catalog_item")
class TestServiceCatalogs:
    '''Services test cases'''
    def test_service_catalog_item(self, svc_catalogs_pg, create_catalog_item):
        '''Order Catalog Item'''
        mylist = create_catalog_item
        cat_name = mylist[1]
        cat_item_name = mylist[2]
        Assert.true(svc_catalogs_pg.is_the_current_page)
        table_pg = svc_catalogs_pg.click_on_service_catalogs_accordion()\
                .select_catalog_in_service_tree(cat_name)
        order_pg = table_pg.select_catalog_item(cat_item_name)
        Assert.true(order_pg.is_the_current_page,
                "not returned to the correct page")
        Assert.equal(order_pg.flash.message,
                "Order Request was Submitted")


    def test_service_catalog_bundle(
            self,
            svc_catalogs_pg,
            create_catalog_bundle):
        '''Order Catalog Bundle'''
        mylist = create_catalog_bundle
        cat_name = mylist[0]
        cat_bundle_name = mylist[1]
        Assert.true(svc_catalogs_pg.is_the_current_page)
        table_pg = svc_catalogs_pg.click_on_service_catalogs_accordion()\
                .select_catalog_in_service_tree(cat_name)
        order_pg = table_pg.select_catalog_item(cat_bundle_name)
        Assert.true(order_pg.is_the_current_page,
                "not returned to the correct page")
        Assert.equal(order_pg.flash.message,
                "Order Request was Submitted")