# -*- coding: utf-8 -*-

import pytest
import time
from time import sleep
from unittestzero import Assert

@pytest.fixture
def virtual_machines_page(home_page_logged_in):
    home_pg = home_page_logged_in
    home_pg._wait_for_results_refresh()
    vm_pg = home_pg.header.site_navigation_menu("Services").sub_navigation_menu("My Services").click()
    vm_pg._wait_for_results_refresh()
    return home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()

@pytest.fixture
def provisioning_start_page(virtual_machines_page):
    vm_pg = virtual_machines_page
    return vm_pg.click_on_provision_vms()

@pytest.fixture(scope="module", # IGNORE:E1101
                params=["linux_template_workflow"])
def provisioning_data(request, cfme_data):
        param = request.param
        return cfme_data.data["provisioning"][param]


@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized", "setup_mgmt_systems", "mgmt_sys_api_clients")

class TestTemplateProvisioning:

    def test_linux_template_cancel(self, mozwebqa, virtual_machines_page, provisioning_start_page, provisioning_data):
        '''Test Cancel button'''
        provisioning_start_page._wait_for_results_refresh()
        template_item_chosen = provisioning_start_page.click_on_template_item(provisioning_data["template"])
        provision_pg = provisioning_start_page.click_on_continue()
        provision_pg.click_on_cancel()
        Assert.true(virtual_machines_page.is_the_current_page, "not returned to the correct page")

    def test_linux_template_workflow(self, mozwebqa, virtual_machines_page, provisioning_start_page, provisioning_data, home_page_logged_in, mgmt_sys_api_clients):
        '''Test Basic Provisioning Workflow'''
        provisioning_start_page._wait_for_results_refresh()
        template_item_chosen = provisioning_start_page.click_on_template_item(provisioning_data["template"])
        provision_pg = provisioning_start_page.click_on_continue()
        self.complete_provision_pages_info(provisioning_data, provision_pg)
        self.assert_vm_state(provisioning_data, home_page_logged_in, "on")
        self.remove_vm(provisioning_data, home_page_logged_in, mgmt_sys_api_clients)


    def complete_provision_pages_info(self, provisioning_data, provision_pg):
        ''' Fills in data for Provisioning tabs'''
        tab_buttons = provision_pg.tabbutton_region
        request_pg = tab_buttons.tabbutton_by_name("Request").click()
        request_pg = request_pg.fill_fields("admin@example.com", "admin", "admin", "Adding a test note", "Manager Name")
        purpose_pg = tab_buttons.tabbutton_by_name("Purpose").click()
        #tree = purpose_pg.click_on_nodes(provisioning_data["node"], provisioning_data["child_node")
        catalog_pg = tab_buttons.tabbutton_by_name("Catalog").click()
        catalog_pg.fill_fields(provisioning_data["provision_type"], str(provisioning_data["count"]),
             provisioning_data["vm_name"], provisioning_data["vm_description"])
        environment_pg = tab_buttons.tabbutton_by_name("Environment").click()
        environment_pg.fill_fields(unicode(provisioning_data["host"]), unicode(provisioning_data["datastore"]))
        hardware_pg = tab_buttons.tabbutton_by_name("Hardware").click()
        network_pg = tab_buttons.tabbutton_by_name("Network").click()
        customize_pg = tab_buttons.tabbutton_by_name("Customize").click()
        schedule_pg = tab_buttons.tabbutton_by_name("Schedule").click()
        schedule_pg.fill_fields(provisioning_data["when_to_provision"], provisioning_data["power_on"], str(provisioning_data["time_until_retirement"]))

        services_requests_pg = provision_pg.click_on_submit()
        Assert.true(services_requests_pg.is_the_current_page, "not returned to the correct page")
        Assert.true(services_requests_pg.flash.message == "VM Provision Request was Submitted, you will be notified when your VMs are ready")
        services_requests_pg.approve_request(1)

    def assert_vm_state(self, provisioning_data, home_page_logged_in, current_state):
        ''' Asserts that the VM is created in the expected state '''
        vm_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
        sleep(180)
        vm_pg.refresh()
        vm_pg.wait_for_vm_state_change(provisioning_data["vm_name"], 'on', 12)
        Assert.true(vm_pg.quadicon_region.get_quadicon_by_title(provisioning_data["vm_name"]).current_state == current_state, "vm not in correct state: " + current_state)

    def remove_vm(self, provisioning_data, home_page_logged_in, mgmt_sys_api_clients):
       '''Powers off and removes the VM'''
       vm_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
       vm_pg.power_off([provisioning_data["vm_name"]])
       Assert.true(vm_pg.flash.message.startswith("Stop initiated"))
       vm_pg.wait_for_vm_state_change(provisioning_data["vm_name"], 'off', 12)
       Assert.true(vm_pg.quadicon_region.get_quadicon_by_title(provisioning_data["vm_name"]).current_state == 'off', "vm running")
       for mgmt_sys in mgmt_sys_api_clients.values():
          if (provisioning_data["vm_name"]+ "/" + provisioning_data["vm_name"] + ".vmx") in mgmt_sys.list_vm() or  provisioning_data["vm_name"] in mgmt_sys.list_vm():
             result = mgmt_sys.delete_vm(provisioning_data["vm_name"])

