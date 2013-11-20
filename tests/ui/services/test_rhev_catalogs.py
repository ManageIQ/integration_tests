'''
Created on July 25th, 2013

@author: Shveta
'''

import pytest
import time
from unittestzero import Assert

@pytest.fixture(scope="module", # IGNORE:E1101
                params=["rhevm_pxe_workflow"])
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
    descr = "descr-" + random_string
    new_dialog_pg.create_service_dialog\
       (random_string, service_dialog_name, descr, "service_name")
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
def create_rhev_catalog_item(
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
    new_cat_item_pg.choose_catalog_item_type('Redhat')
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
            provisioning_data["provision_type"],
            provisioning_data["pxe_server"],
            provisioning_data["server_image"],
            0, vm_name)
    envt_pg = req_pg.click_on_environment_tab()
    new_pg = envt_pg.fill_environment_tab(
               None, None, None,
               unicode(provisioning_data["host"]),
               unicode(provisioning_data["datastore"]))
    hardware_pg = new_pg.click_on_hardware_tab()
    network_pg = hardware_pg.click_on_network_tab()
    try:
        if ("PXE" in provisioning_data["provision_type"]) or \
            ("ISO" in provisioning_data["provision_type"]):
            customize_pg = network_pg.click_on_customize_tab()
            save_pg = customize_pg.fill_customize_tab(
                provisioning_data["root_password"],
                provisioning_data["address_node_value"],
                provisioning_data["customization_template"])
        save_pg.save_catalog_item()
    except:
        Assert.fail("Unable to create catalog item, " +
                "check for duplicate infra providers")
    names = [service_dialog_name, catalog_name, catalog_item_name,
            provisioning_data["provider_key"], vm_name]
    return names

@pytest.mark.nondestructive
@pytest.mark.usefixtures(
        "server_roles",
        "setup_infrastructure_providers",
         "setup_pxe_provision",
        "mgmt_sys_api_clients")
@pytest.mark.fixtureconf(server_roles="+automate")
class TestRhevCatalogs:
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
            # TODO: We probably should be watching the request
            # status vs time counting
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
            
    def test_order_rhev_service_catalog_item(
            self,
            mgmt_sys_api_clients,
            cfme_data,
            create_rhev_catalog_item,
            svc_catalogs_pg):
        '''Order Catalog Item'''
        mylist = create_rhev_catalog_item
        cat_name = mylist[1]
        cat_item_name = mylist[2]
        prov_key = mylist[3]
        vm_name = mylist[4]
        Assert.true(svc_catalogs_pg.is_the_current_page)
        table_pg = svc_catalogs_pg.click_on_service_catalogs_accordion()\
                .select_catalog_in_service_tree(cat_name)
        order_pg = table_pg.select_catalog_item(cat_item_name ,
                    "service_"+cat_item_name)
        Assert.equal(order_pg.flash.message, "Order Request was Submitted")
        order_pg.approve_request(1)
        order_pg.wait_for_request_status("Last 24 Hours",
            "Finished", 12)
        # cleanup
        self._check_vm_provision(mgmt_sys_api_clients, prov_key,
                vm_name+"_0001")
        
    