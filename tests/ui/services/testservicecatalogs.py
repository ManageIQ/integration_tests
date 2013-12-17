'''
Created on July 25th, 2013

@author: Shveta
'''

import pytest
from unittestzero import Assert
from tests.ui.services.testbasecatalogs import TestBaseCatalogs


@pytest.mark.nondestructive
@pytest.mark.fixtureconf(server_roles='+automate')
@pytest.mark.usefixtures(
    "setup_cloud_providers",
    "setup_infrastructure_providers",
    "mgmt_sys_api_clients",
    "db_session",
    "soap_client")
class TestAllCatalogs(TestBaseCatalogs):
    def test_order_service_catalog_item(
            self,
            server_roles,
            mgmt_sys_api_clients,
            provisioning_data,
            create_service_dialog,
            create_catalog,
            svc_catalogs_pg,
            random_name,
            db_session,
            soap_client):
        '''Test Basic Provisioning Workflow'''
        service_dialog_name = create_service_dialog
        catalog_name = create_catalog
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
        self.complete_sc_pages_info(provisioning_data,
            req_pg, random_name, vm_name)
        table_pg = svc_catalogs_pg.click_on_service_catalogs_accordion()\
            .select_catalog_in_service_tree(catalog_name)
        order_pg = table_pg.select_catalog_item(cat_item_name,
                    "service_" + cat_item_name)
        Assert.equal(order_pg.flash.message, "Order Request was Submitted")
        order_pg.approve_request(1)
        order_pg.wait_for_request_status("Last 24 Hours",
            "Finished", 12)
        self.assert_vm_state(provisioning_data, svc_catalogs_pg,
            "on", (vm_name + "_0001"))
        self.teardown_remove_from_provider(db_session, soap_client,
            mgmt_sys_api_clients,
            vm_name + "_0001")

    def test_order_service_catalog_bundle(
            self,
            mgmt_sys_api_clients,
            provisioning_data,
            random_name,
            create_service_dialog,
            create_catalog,
            db_session,
            soap_client,
            svc_catalogs_pg):
        '''Order Catalog Bundle'''
        service_dialog_name = create_service_dialog
        catalog_name = create_catalog
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
        self.complete_sc_pages_info(provisioning_data,
            req_pg, random_name, vm_name)
        cat_bundle_name = self.create_catalog_bundle(random_name,
            provisioning_data,
            svc_catalogs_pg,
            catalog_name,
            service_dialog_name,
            cat_item_name)
        Assert.true(svc_catalogs_pg.is_the_current_page)
        table_pg = svc_catalogs_pg.click_on_service_catalogs_accordion()\
            .select_catalog_in_service_tree(catalog_name)
        order_pg = table_pg.select_catalog_item(cat_bundle_name,
                    "service_" + cat_bundle_name)
        Assert.equal(order_pg.flash.message, "Order Request was Submitted")
        order_pg.approve_request(1)
        order_pg.wait_for_request_status("Last 24 Hours",
            "Finished", 12)
        self.assert_vm_state(provisioning_data, svc_catalogs_pg,
            "on", (vm_name + "_0001"))
        self.teardown_remove_from_provider(db_session, soap_client,
            mgmt_sys_api_clients,
            vm_name + "_0001")

    def test_delete_catalog_deletes_service(
            self,
            provisioning_data,
            random_name,
            create_service_dialog,
            create_catalog,
            svc_catalogs_pg):
        '''Delete Catalog should delete service'''
        service_dialog_name = create_service_dialog
        catalog_name = create_catalog
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
        self.complete_sc_pages_info(provisioning_data,
            req_pg, random_name, vm_name)
        #mylist = create_catalog_item
        #cat_name = mylist[1]
        Assert.true(svc_catalogs_pg.is_the_current_page)
        delete_pg = svc_catalogs_pg.click_on_catalogs_accordion().\
            click_on_catalog(catalog_name)
        delete_pg.delete_catalog()
        Assert.false(svc_catalogs_pg.click_on_service_catalogs_accordion().
            is_catalog_present(catalog_name), "service catalog not found")

    def test_delete_catalog_item_deletes_service(
            self,
            provisioning_data,
            random_name,
            create_service_dialog,
            create_catalog,
            svc_catalogs_pg):
        '''Delete Catalog should delete service'''
        service_dialog_name = create_service_dialog
        catalog_name = create_catalog
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
        self.complete_sc_pages_info(provisioning_data,
            req_pg, random_name, vm_name)
        #mylist = create_catalog_item
        #cat_name = mylist[1]
        #cat_item = mylist[2]
        Assert.true(svc_catalogs_pg.is_the_current_page)
        delete_pg = svc_catalogs_pg.click_on_catalog_item_accordion().\
            click_on_catalog_item(cat_item_name)
        delete_pg.delete_catalog_item()
        Assert.false(svc_catalogs_pg.click_on_service_catalogs_accordion().
        is_catalog_item_present(cat_item_name), "service catalog item not found")

    def test_service_circular_reference_not_allowed(
            self,
            random_name,
            provisioning_data,
            create_service_dialog,
            create_catalog,
            svc_catalogs_pg):
        '''service calling itself should not be allowed'''
        service_dialog_name = create_service_dialog
        catalog_name = create_catalog
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
        self.complete_sc_pages_info(provisioning_data,
            req_pg, random_name, vm_name)
        cat_bundle_name = self.create_catalog_bundle(random_name,
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
        Assert.true(res_pg.flash.message.startswith(
            'Catalog Bundle "%s" was added' % sec_catalog_bundle))
        # Edit first catalog bundle to call second
        edit_pg = svc_catalogs_pg.click_on_catalog_item_accordion().\
            click_on_catalog_item(cat_bundle_name)
        reso_pg = edit_pg.edit_catalog_bundle()
        resource_pg = reso_pg.click_on_resources_tab()
        resource_pg.select_catalog_item_and_edit(sec_catalog_bundle)
        Assert.equal(resource_pg.flash.message,
            "Error during 'Resource Add': Adding resource <%s> to Service <%s> will create a circular reference"
            % (sec_catalog_bundle, cat_bundle_name))

    def test_service_name_change_script(
            self,
            check_service_name,
            svc_myservices_pg):
        '''test automate script to change service name'''
        service_name = check_service_name
        svc_myservices_pg.select_service_in_tree(service_name)
        Assert.true(svc_myservices_pg.is_service_present(service_name), "service not found")
