import pytest

# -*- coding: utf-8 -*-
from utils.conf import cfme_data
import db


def complete_sc_pages_info(provisioning_data, catalog_pg, random_name, vm_name):
    ''' Fills in data for Provisioning tabs'''
    tab_buttons = catalog_pg.tabbutton_region
    catalog_pg.fill_catalog_tab(
        provisioning_data["template"],
        provisioning_data["provision_type"],
        provisioning_data["pxe_server"],
        provisioning_data["server_image"],
        cfme_data["management_systems"][provisioning_data["provider_key"]]["name"],
        0, vm_name)
    environment_pg = tab_buttons.tabbutton_by_name("Environment").click()
    environment_pg.fill_fields(
        provisioning_data["datacenter"],
        provisioning_data["cluster"],
        provisioning_data["resource_pool"],
        unicode(provisioning_data["host"]),
        unicode(provisioning_data["datastore"]),
        provisioning_data["availability_zone"],
        provisioning_data["security_group"])
    if provisioning_data["availability_zone"] is not None:
        properties_pg = tab_buttons.tabbutton_by_name("Properties").click()
        properties_pg.fill_fields(
            provisioning_data["instance_type"],
            provisioning_data["key_pair"],
            provisioning_data["public_ip_address"])
    else:
        tab_buttons.tabbutton_by_name("Hardware").click()
        tab_buttons.tabbutton_by_name("Network").click()
    if provisioning_data["provision_type"] is not None:
        if ("PXE" in provisioning_data["provision_type"]) or \
                ("ISO" in provisioning_data["provision_type"]):
            customize_pg = tab_buttons.tabbutton_by_name("Customize").click()
            customize_pg.fill_fields(
                provisioning_data["root_password"],
                provisioning_data["address_node_value"],
                provisioning_data["customization_template"])
    schedule_pg = tab_buttons.tabbutton_by_name("Schedule").click()
    schedule_pg.fill_fields(
        None,
        provisioning_data["power_on"],
        str(provisioning_data["time_until_retirement"]))
    catalog_pg.save_catalog_item()


def create_catalog_bundle(random_string, provisioning_data, svc_catalogs_pg, cat_name,
        service_dialog, cat_item_name):
    '''Fixture to create Catalog item and bundle'''
    new_bundle_pg = svc_catalogs_pg.click_on_catalog_item_accordion()\
        .add_new_catalog_bundle()
    catalog_bundle_name = "auto_bundle_" + random_string
    new_bundle_pg.fill_bundle_basic_info(
        catalog_bundle_name,
        "bundle_desc_" + random_string,
        cat_name,
        service_dialog)
    res_pg = new_bundle_pg.click_on_resources_tab()
    res_pg.select_catalog_item_and_add(cat_item_name)
    return catalog_bundle_name


def assert_vm_state(provisioning_data, current_page, current_state, vm_name):
    ''' Asserts that the VM is created in the expected state '''
    if provisioning_data["availability_zone"] is not None:
        vm_pg = current_page.header.site_navigation_menu(
            'Clouds').sub_navigation_menu(
            'Instances').click()
        vm_pg.refresh()
        vm_pg.wait_for_state_change(vm_name, current_state, 12)
    else:
        vm_pg = current_page.header.site_navigation_menu(
            'Infrastructure').sub_navigation_menu(
            'Virtual Machines').click()
        vm_pg.refresh()
        vm_pg.wait_for_vm_state_change(vm_name, current_state, 12)
    assert vm_pg.quadicon_region.get_quadicon_by_title(vm_name).current_state == current_state
    return vm_pg


def teardown_remove_from_provider(db_session, provisioning_data, soap_client,
        mgmt_sys_api_clients, vm_name):
    '''Stops a VM and removes VM or Template from provider'''
    for name, guid, power_state, template in db_session.query(
            db.Vm.name, db.Vm.guid, db.Vm.power_state, db.Vm.template):
        if vm_name in name:
            if power_state == 'on':
                result = soap_client.service.EVMSmartStop(guid)
                assert result.result == 'true'
                break
            else:
                print "Template found or VM is off"
                if template:
                    print "Template to be deleted from provider"
                    soap_client.service.EVMDeleteVmByName(vm_name)
                break
    else:
        raise Exception("Couldn't find VM or Template")
    vm_stopped = mgmt_sys_api_clients[provisioning_data["provider_key"]]\
        .is_vm_stopped(vm_name)
    if vm_stopped:
        mgmt_sys_api_clients[provisioning_data["provider_key"]].delete_vm(vm_name)


@pytest.mark.fixtureconf(server_roles='+automate')
@pytest.mark.usefixtures("server_roles", "setup_infrastructure_providers",
    "setup_pxe_provision", "mgmt_sys_api_clients", "db_session", "soap_client")
def test_order_service_catalog_item(mgmt_sys_api_clients, provisioning_data,
        service_dialog, catalog, svc_catalogs_pg, random_name, db_session, soap_client):
    '''Test Basic Provisioning Workflow'''
    service_dialog_name = service_dialog
    catalog_name = catalog
    new_cat_item_pg = svc_catalogs_pg.click_on_catalog_item_accordion().\
        add_new_catalog_item()
    new_cat_item_pg.choose_catalog_item_type(provisioning_data["catalog_item_type"])
    cat_item_name = "auto_item_" + random_name
    new_cat_item_pg.fill_basic_info(
        cat_item_name,
        "item_desc_" + random_name,
        catalog_name,
        service_dialog_name)
    vm_name = "vm_name" + random_name
    req_pg = new_cat_item_pg.click_on_request_info_tab()
    complete_sc_pages_info(provisioning_data,
        req_pg, random_name, vm_name)
    table_pg = svc_catalogs_pg.click_on_service_catalogs_accordion()\
        .select_catalog_in_service_tree(catalog_name)
    order_pg = table_pg.select_catalog_item(cat_item_name,
                "service_" + cat_item_name)
    assert order_pg.flash.message == "Order Request was Submitted"
    request_id = order_pg.approve_request(1)
    order_pg.wait_for_request_status("Last 24 Hours",
        "Finished", 12, request_id)
    assert_vm_state(provisioning_data, svc_catalogs_pg,
        "on", (vm_name + "_0001"))
    teardown_remove_from_provider(db_session, provisioning_data, soap_client,
        mgmt_sys_api_clients,
        vm_name + "_0001")


def test_order_service_catalog_bundle(mgmt_sys_api_clients, provisioning_data,
        random_name, service_dialog, catalog, db_session, soap_client, svc_catalogs_pg):
    '''Order Catalog Bundle'''
    service_dialog_name = service_dialog
    catalog_name = catalog
    new_cat_item_pg = svc_catalogs_pg.click_on_catalog_item_accordion().\
        add_new_catalog_item()
    new_cat_item_pg.choose_catalog_item_type(provisioning_data["catalog_item_type"])
    cat_item_name = "auto_item_" + random_name
    new_cat_item_pg.fill_basic_info(
        cat_item_name,
        "item_desc_" + random_name,
        catalog_name,
        service_dialog_name)
    vm_name = "vm_name" + random_name
    req_pg = new_cat_item_pg.click_on_request_info_tab()
    complete_sc_pages_info(provisioning_data,
        req_pg, random_name, vm_name)
    cat_bundle_name = create_catalog_bundle(random_name,
        provisioning_data,
        svc_catalogs_pg,
        catalog_name,
        service_dialog_name,
        cat_item_name)
    svc_catalogs_pg.is_the_current_page
    table_pg = svc_catalogs_pg.click_on_service_catalogs_accordion()\
        .select_catalog_in_service_tree(catalog_name)
    order_pg = table_pg.select_catalog_item(cat_bundle_name,
                "service_" + cat_bundle_name)
    assert order_pg.flash.message == "Order Request was Submitted"
    request_id = order_pg.approve_request(1)
    order_pg.wait_for_request_status("Last 24 Hours",
        "Finished", 12, request_id)
    assert_vm_state(provisioning_data, svc_catalogs_pg,
        "on", (vm_name + "_0001"))
    teardown_remove_from_provider(db_session, provisioning_data, soap_client,
        mgmt_sys_api_clients,
        vm_name + "_0001")


def test_delete_catalog_deletes_service(provisioning_data, random_name, service_dialog,
        catalog, svc_catalogs_pg):
    '''Delete Catalog should delete service'''
    service_dialog_name = service_dialog
    catalog_name = catalog
    new_cat_item_pg = svc_catalogs_pg.click_on_catalog_item_accordion().\
        add_new_catalog_item()
    new_cat_item_pg.choose_catalog_item_type(provisioning_data["catalog_item_type"])
    cat_item_name = "auto_item_" + random_name
    new_cat_item_pg.fill_basic_info(
        cat_item_name,
        "item_desc_" + random_name,
        catalog_name,
        service_dialog_name)
    vm_name = "vm_name" + random_name
    req_pg = new_cat_item_pg.click_on_request_info_tab()
    complete_sc_pages_info(provisioning_data,
        req_pg, random_name, vm_name)
    svc_catalogs_pg.is_the_current_page
    delete_pg = svc_catalogs_pg.click_on_catalogs_accordion().\
        click_on_catalog(catalog_name)
    delete_pg.delete_catalog()
    assert not svc_catalogs_pg.click_on_service_catalogs_accordion()\
        .is_catalog_present(catalog_name), "service catalog not found"


def test_delete_catalog_item_deletes_service(provisioning_data, random_name,
        service_dialog, catalog, svc_catalogs_pg):
    '''Delete Catalog should delete service'''
    service_dialog_name = service_dialog
    catalog_name = catalog
    new_cat_item_pg = svc_catalogs_pg.click_on_catalog_item_accordion().\
        add_new_catalog_item()
    new_cat_item_pg.choose_catalog_item_type(provisioning_data["catalog_item_type"])
    cat_item_name = "auto_item_" + random_name
    new_cat_item_pg.fill_basic_info(
        cat_item_name,
        "item_desc_" + random_name,
        catalog_name,
        service_dialog_name)
    vm_name = "vm_name" + random_name
    req_pg = new_cat_item_pg.click_on_request_info_tab()
    complete_sc_pages_info(provisioning_data,
        req_pg, random_name, vm_name)
    svc_catalogs_pg.is_the_current_page
    delete_pg = svc_catalogs_pg.click_on_catalog_item_accordion()\
        .click_on_catalog_item(cat_item_name)
    delete_pg.delete_catalog_item()
    assert not svc_catalogs_pg.click_on_service_catalogs_accordion()\
        .is_catalog_item_present(cat_item_name), "service catalog item not found"


def test_service_circular_reference_not_allowed(random_name, provisioning_data,
        service_dialog, catalog, svc_catalogs_pg):
    '''service calling itself should not be allowed'''
    service_dialog_name = service_dialog
    catalog_name = catalog
    new_cat_item_pg = svc_catalogs_pg.click_on_catalog_item_accordion().\
        add_new_catalog_item()
    new_cat_item_pg.choose_catalog_item_type(provisioning_data["catalog_item_type"])
    cat_item_name = "auto_item_" + random_name
    new_cat_item_pg.fill_basic_info(
        cat_item_name,
        "item_desc_" + random_name,
        catalog_name,
        service_dialog_name)
    vm_name = "vm_name" + random_name
    req_pg = new_cat_item_pg.click_on_request_info_tab()
    complete_sc_pages_info(provisioning_data,
        req_pg, random_name, vm_name)
    cat_bundle_name = create_catalog_bundle(random_name,
        provisioning_data,
        svc_catalogs_pg,
        catalog_name,
        service_dialog_name,
        cat_item_name)
    new_bundle_pg = svc_catalogs_pg.click_on_catalog_item_accordion()\
        .add_new_catalog_bundle()
    sec_catalog_bundle = "sec_auto_bundle" + random_name
    new_bundle_pg.fill_bundle_basic_info(sec_catalog_bundle,
        "bundle_desc_" + random_name,
        catalog_name, service_dialog_name)
    res_pg = new_bundle_pg.click_on_resources_tab()
    # second catalog bundle calling first
    res_pg.select_catalog_item_and_add(cat_bundle_name)
    assert res_pg.flash.message.startswith(
        'Catalog Bundle "%s" was added' % sec_catalog_bundle)
    # Edit first catalog bundle to call second
    edit_pg = svc_catalogs_pg.click_on_catalog_item_accordion().\
        click_on_catalog_item(cat_bundle_name)
    reso_pg = edit_pg.edit_catalog_bundle()
    resource_pg = reso_pg.click_on_resources_tab()
    resource_pg.select_catalog_item_and_edit(sec_catalog_bundle)
    assert resource_pg.flash.message == ("Error during 'Resource Add': Adding resource <%s> to "
        "Service <%s> will create a circular reference") % (sec_catalog_bundle, cat_bundle_name)


def test_service_name_change_script(check_service_name, svc_myservices_pg):
    '''test automate script to change service name'''
    service_name = check_service_name
    svc_myservices_pg.select_service_in_tree(service_name)
    assert svc_myservices_pg.is_service_present(service_name), "service not found"
