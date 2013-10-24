'''
Created on July 25th, 2013

@author: Shveta
'''

import pytest
import time
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
def create_catalog_item(
        maximized,
        random_string, 
        provisioning_data,
        setup_infrastructure_providers,
        create_service_dialog, 
        svc_catalogs_pg, 
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
            service_dialog_name)
    req_pg = new_cat_item_pg.click_on_request_info_tab()
    vm_name = "vm_name" + random_string
    req_pg.fill_catalog_tab(
            provisioning_data["template"],
            vm_name)
    envt_pg = req_pg.click_on_environment_tab()
    try:
        envt_pg.fill_environment_tab(
                unicode(provisioning_data["host"]),
                unicode(provisioning_data["datastore"]))
    except:
        Assert.fail("Unable to create catalog item, " + 
                "check for duplicate infra providers")    
    names = [service_dialog_name, catalog_name, catalog_item_name, 
            provisioning_data["provider_key"], vm_name]
    return names

@pytest.fixture()
def create_catalog_bundle(
        random_string, 
        provisioning_data, 
        svc_catalogs_pg, 
        create_catalog_item):
    '''Fixture to create Catalog item and bundle'''
    cat_list = create_catalog_item
    cat_name = cat_list[1]
    vm_name = cat_list[4]
    new_bundle_pg = svc_catalogs_pg.click_on_catalog_item_accordion()\
            .add_new_catalog_bundle()
    catalog_bundle_name = "auto_bundle_" + random_string
    new_bundle_pg.fill_bundle_basic_info(
            catalog_bundle_name,
            "bundle_desc_" + random_string,
            cat_list[1],
            cat_list[0])
    res_pg = new_bundle_pg.click_on_resources_tab()
    res_pg.select_catalog_item_and_add(cat_list[2])
    item_names = [cat_name, catalog_bundle_name, cat_list[0], 
            provisioning_data["provider_key"], vm_name]
    return item_names

@pytest.mark.nondestructive
@pytest.mark.usefixtures(
        "maximized",
        "server_roles",
        "setup_infrastructure_providers",
        "create_catalog_item",
        "mgmt_sys_api_clients")
@pytest.mark.fixtureconf(server_roles="+automate")
class TestServiceCatalogs:
    '''Services test cases'''
    
    def _check_vm_provision(
            self, 
            mgmt_sys_api_clients, 
            provider_key, 
            vm_name):
        ''' Waits for provision, allows startup, and then deletes 
                provisioned vm/instance'''
        count = 0
        while (count <= 600):
            try:
                vm_running = mgmt_sys_api_clients[provider_key]\
                        .is_vm_running(vm_name)
                if vm_running:
                    mgmt_sys_api_clients[provider_key].stop_vm(vm_name)
                    time.sleep(30)
                    break
            except:
                pass
            time.sleep(60)
            count += 60
        if count > 600:
            # We are going to need to see how this goes, I have seen some requests 
            #   take 20 minutes to approve.
            #
            # TODO: We probably should be watching the request status vs time counting
            Assert.fail("vm never provisioned after 10 minutes")
        Assert.true(mgmt_sys_api_clients[provider_key].is_vm_stopped(vm_name),
                "vm never stopped")
        # cleanup/delete provisioned vm
        count = 0
        while (count <= 600):
            vm_stopped = mgmt_sys_api_clients[provider_key]\
                    .is_vm_stopped(vm_name)
            if vm_stopped:
                    mgmt_sys_api_clients[provider_key].delete_vm(vm_name)
                    break
            time.sleep(60)
            count += 60

    def test_order_service_catalog_item(
            self, 
            mgmt_sys_api_clients,
            cfme_data,
            create_catalog_item,
            svc_catalogs_pg):
        '''Order Catalog Item'''
        mylist = create_catalog_item
        cat_name = mylist[1]
        cat_item_name = mylist[2]
        prov_key = mylist[3]
        vm_name = mylist[4]
        Assert.true(svc_catalogs_pg.is_the_current_page)
        table_pg = svc_catalogs_pg.click_on_service_catalogs_accordion()\
                .select_catalog_in_service_tree(cat_name)
        order_pg = table_pg.select_catalog_item(cat_item_name)
        Assert.true(order_pg.is_the_current_page,
            "not returned to the correct page")
        Assert.equal(order_pg.flash.message, "Order Request was Submitted")
        # cleanup
        self._check_vm_provision(mgmt_sys_api_clients, prov_key, 
                vm_name+"_0001")

    def test_order_service_catalog_bundle(
            self, 
            mgmt_sys_api_clients,
            cfme_data,
            create_catalog_bundle,
            svc_catalogs_pg):
        '''Order Catalog Bundle'''
        mylist = create_catalog_bundle
        cat_name = mylist[0]
        prov_key = mylist[3]
        vm_name = mylist[4]
        cat_bundle_name = mylist[1]
        Assert.true(svc_catalogs_pg.is_the_current_page)
        table_pg = svc_catalogs_pg.click_on_service_catalogs_accordion()\
            .select_catalog_in_service_tree(cat_name)
        order_pg = table_pg.select_catalog_item(cat_bundle_name)
        Assert.true(order_pg.is_the_current_page,
            "not returned to the correct page")
        Assert.equal(order_pg.flash.message,"Order Request was Submitted")
        # cleanup
        self._check_vm_provision(mgmt_sys_api_clients, prov_key, 
                vm_name+"_0001")

    def test_delete_catalog_deletes_service(
            self, 
            svc_catalogs_pg, 
            create_catalog_item):
        '''Delete Catalog should delete service'''
        mylist = create_catalog_item
        cat_name = mylist[1]
        Assert.true(svc_catalogs_pg.is_the_current_page)
        delete_pg = svc_catalogs_pg.click_on_catalogs_accordion().\
            click_on_catalog(cat_name)
        show_cat_pg = delete_pg.delete_catalog()
        Assert.false(svc_catalogs_pg.click_on_service_catalogs_accordion().\
            is_catalog_present(cat_name),"service catalog not found")

    def test_delete_catalog_item_deletes_service(
            self, 
            create_catalog_item, 
            svc_catalogs_pg):
        '''Delete Catalog should delete service'''
        mylist = create_catalog_item
        cat_name = mylist[1]
        cat_item = mylist[2]
        Assert.true(svc_catalogs_pg.is_the_current_page)
        delete_pg = svc_catalogs_pg.click_on_catalog_item_accordion().\
                    click_on_catalog_item(cat_item)
        show_cat_pg = delete_pg.delete_catalog_item()
        Assert.false(svc_catalogs_pg.click_on_service_catalogs_accordion().\
        is_catalog_item_present(cat_item),"service catalog item not found")

    def test_service_circular_reference_not_allowed(
            self, 
            random_string,
            svc_catalogs_pg, 
            create_catalog_bundle):
        '''service calling itself should not be allowed'''
        mylist = create_catalog_bundle
        cat_name = mylist[0]
        cat_bundle_name = mylist[1]
        serv_dialog_name = mylist[2]
        '''second catalog bundle'''
        new_bundle_pg = svc_catalogs_pg.click_on_catalog_item_accordion()\
            .add_new_catalog_bundle()
        sec_catalog_bundle = "sec_auto_bundle" + random_string
        new_bundle_pg.fill_bundle_basic_info(sec_catalog_bundle,
            "bundle_desc_" + random_string,
            cat_name, serv_dialog_name)
        res_pg = new_bundle_pg.click_on_resources_tab()
        '''second catalog bundle calling first'''
        res_pg.select_catalog_item_and_add(cat_bundle_name)
        Assert.true(res_pg.flash.message.startswith(
            'Catalog Bundle "%s" was added' % sec_catalog_bundle))
        '''Edit first catalog bundle to call second'''
        edit_pg = svc_catalogs_pg.click_on_catalog_item_accordion().\
                    click_on_catalog_item(cat_bundle_name)
        reso_pg = edit_pg.edit_catalog_bundle()
        resource_pg = reso_pg.click_on_resources_tab()
        resource_pg.select_catalog_item_and_edit(sec_catalog_bundle)
        Assert.equal(resource_pg.flash.message,
            "Error during 'Resource Add': Adding resource <%s> to Service <%s> will create a circular reference"
            % (sec_catalog_bundle ,cat_bundle_name))
