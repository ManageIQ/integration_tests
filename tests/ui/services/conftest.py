# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest


@pytest.fixture
def provisioning_start_page(infra_vms_pg):
    '''Navigates to the page to start provisioning'''
    vm_pg = infra_vms_pg
    return vm_pg.click_on_provision_vms()


@pytest.fixture()
def create_service_dialog(automate_customization_pg,
    random_string, provisioning_data):
    '''Fixture to create Catalog item and bundle'''
    new_dialog_pg = automate_customization_pg\
        .click_on_service_dialog_accordion().add_new_service_dialog()
    service_dialog_name = "auto_dialog_" + random_string
    descr = "descr-" + random_string
    new_dialog_pg.create_service_dialog(random_string, service_dialog_name, descr, "service_name")
    return service_dialog_name


@pytest.fixture()
def create_catalog(
        svc_catalogs_pg,
        random_string,
        provisioning_data):
        '''Fixture to create Catalog item and bundle'''
        new_cat_pg = svc_catalogs_pg.click_on_catalogs_accordion()\
            .add_new_catalog()
        catalog_name = "auto_cat_" + random_string
        new_cat_pg.fill_basic_info_tab(catalog_name, "descr_" + random_string)
        return catalog_name


@pytest.fixture()
def check_service_name(
        random_string,
        create_service_name_script,
        create_generic_catalog_item,
        svc_catalogs_pg):
    '''test automate script to change service name'''
    catalog_item_name, catalog_name = create_generic_catalog_item
    table_pg = svc_catalogs_pg.click_on_service_catalogs_accordion()\
        .select_catalog_in_service_tree(catalog_name)
    service_name = "changed_name_" + random_string
    order_pg = table_pg.select_catalog_item(catalog_item_name, service_name)
    order_pg.approve_request(1)
    order_pg.wait_for_request_status("Last 24 Hours",
        "Finished", 12)
    return service_name


@pytest.fixture()
def create_service_name_script(automate_explorer_pg):
    '''Fixture to specify service name change script'''
    ae_namespace_pg = automate_explorer_pg.click_on_class_access_node(
        "Service Provision State Machine (ServiceProvision_Template)")
    ae_namespace_pg.select_instance_item("default")
    inst_pg = ae_namespace_pg.click_on_edit_this_instance()
    inst_pg.fill_instance_field_row_info(1,
            "/Sample/Methods/servicename_sample")
    inst_pg.click_on_save_button()


@pytest.fixture()
def create_generic_catalog_item(random_string,
        create_service_dialog,
        svc_catalogs_pg,
        create_catalog):
    '''Fixture to create generic item'''
    service_dialog_name = create_service_dialog
    catalog_name = create_catalog
    new_cat_item_pg = svc_catalogs_pg.click_on_catalog_item_accordion().\
        add_new_catalog_item()
    new_cat_item_pg.choose_catalog_item_type('Generic')
    catalog_item_name = "auto_item_" + random_string
    entry_pg = new_cat_item_pg.fill_basic_info(
        catalog_item_name,
        "item_desc_" + random_string,
        catalog_name,
        service_dialog_name)
    save_pg = entry_pg.fill_provisioning_entry_point(
        "Service Provision State Machine (ServiceProvision_Template)")
    save_pg.save_catalog_item()
    return catalog_item_name, catalog_name


@pytest.fixture(scope="module",  # IGNORE:E1101
               params=["linux_template_workflow",
               "rhevm_pxe_workflow",
               "ec2_image_workflow"])
def provisioning_data(request, cfme_data):
    '''Returns all provisioning data'''
    param = request.param
    return cfme_data["provisioning"][param]


@pytest.fixture
def random_name(random_string):
    '''Returns random name addition for vms'''
    return '_%s' % random_string


@pytest.fixture
def enables_automation_engine(cnf_configuration_pg):
    '''Enables Automate Engine in Configure'''
    conf_pg = cnf_configuration_pg
    conf_pg.click_on_settings()
    return conf_pg.enable_automation_engine()

