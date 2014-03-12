# -*- coding: utf-8 -*-
# pylint: disable=W0621
from unittestzero import Assert
from utils.conf import cfme_data
import db


class TestBaseCatalogs:

    def complete_sc_pages_info(self,
            provisioning_data, catalog_pg, random_name, vm_name):
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
            hardware_pg = tab_buttons.tabbutton_by_name("Hardware").click()
            network_pg = tab_buttons.tabbutton_by_name("Network").click()
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

    def create_catalog_bundle(self,
        random_string,
        provisioning_data,
        svc_catalogs_pg,
        cat_name,
        service_dialog,
        cat_item_name):
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

    def assert_vm_state(self, provisioning_data, current_page,
            current_state, vm_name):
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
        Assert.equal(vm_pg.quadicon_region.get_quadicon_by_title(vm_name)
            .current_state, current_state,
            "vm not in correct state: " + current_state)
        return vm_pg

    def teardown_remove_from_provider(
            self,
            db_session,
            provisioning_data,
            soap_client,
            mgmt_sys_api_clients,
            vm_name):
        '''Stops a VM and removes VM or Template from provider'''
        for name, guid, power_state, template in db_session.query(
                db.Vm.name, db.Vm.guid, db.Vm.power_state, db.Vm.template):
            if vm_name in name:
                if power_state == 'on':
                    result = soap_client.service.EVMSmartStop(guid)
                    Assert.equal(result.result, 'true')
                    break
                else:
                    print "Template found or VM is off"
                    if template:
                        print "Template to be deleted from provider"
                        provider = mgmt_sys_api_clients.values()[0]
                        soap_client.service.EVMDeleteVmByName(vm_name)
                    break
        else:
            raise Exception("Couldn't find VM or Template")
        vm_stopped = mgmt_sys_api_clients[provisioning_data["provider_key"]]\
            .is_vm_stopped(vm_name)
        if vm_stopped:
            mgmt_sys_api_clients[provisioning_data["provider_key"]].delete_vm(vm_name)
