# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest
from time import sleep
from unittestzero import Assert

@pytest.fixture
def provisioning_start_page(infra_vms_pg):
    return infra_vms_pg.click_on_provision_vms()

@pytest.fixture(scope="module", # IGNORE:E1101
                params=["linux_template_workflow"])
def provisioning_data(request, cfme_data):
    param = request.param
    return cfme_data.data["provisioning"][param]


@pytest.mark.nondestructive
@pytest.mark.usefixtures(
        "maximized",
        "setup_infrastructure_providers",
        "mgmt_sys_api_clients")
class TestTemplateProvisioning:

    def test_linux_template_cancel(
            self,
            provisioning_start_page,
            provisioning_data):
        '''Test Cancel button'''
        provisioning_start_page.click_on_template_item(
                provisioning_data["template"])
        provision_pg = provisioning_start_page.click_on_continue()
        vm_pg = provision_pg.click_on_cancel()
        Assert.true(vm_pg.is_the_current_page,
                "not returned to the correct page")

    def test_linux_template_workflow(
            self,
            provisioning_start_page,
            provisioning_data,
            mgmt_sys_api_clients):
        '''Test Basic Provisioning Workflow'''
        provisioning_start_page.click_on_template_item(
                provisioning_data["template"])
        provision_pg = provisioning_start_page.click_on_continue()
        self.complete_provision_pages_info(provisioning_data, provision_pg)
        vm_pg = assert_vm_state(provisioning_data, provision_pg, "on")
        remove_vm(provisioning_data, vm_pg, mgmt_sys_api_clients)

    def complete_provision_pages_info(self, provisioning_data, provision_pg):
        ''' Fills in data for Provisioning tabs'''
        tab_buttons = provision_pg.tabbutton_region
        request_pg = tab_buttons.tabbutton_by_name("Request").click()
        request_pg = request_pg.fill_fields(
                "admin@example.com",
                "admin",
                "admin",
                "Adding a test note",
                "Manager Name")
        purpose_pg = tab_buttons.tabbutton_by_name("Purpose").click()
        # tree = purpose_pg.click_on_nodes(provisioning_data["node"],
        #        provisioning_data["child_node")
        catalog_pg = tab_buttons.tabbutton_by_name("Catalog").click()
        catalog_pg.fill_fields(
                provisioning_data["provision_type"],
                str(provisioning_data["count"]),
                provisioning_data["vm_name"],
                provisioning_data["vm_description"])
        environment_pg = tab_buttons.tabbutton_by_name("Environment").click()
        environment_pg.fill_fields(
                unicode(provisioning_data["host"]),
                unicode(provisioning_data["datastore"]))
        hardware_pg = tab_buttons.tabbutton_by_name("Hardware").click()
        network_pg = tab_buttons.tabbutton_by_name("Network").click()
        customize_pg = tab_buttons.tabbutton_by_name("Customize").click()
        schedule_pg = tab_buttons.tabbutton_by_name("Schedule").click()
        schedule_pg.fill_fields(
                provisioning_data["when_to_provision"],
                provisioning_data["power_on"],
                str(provisioning_data["time_until_retirement"]))

        services_requests_pg = schedule_pg.click_on_submit()
        Assert.true(services_requests_pg.is_the_current_page,
                "not returned to the correct page")
        Assert.equal(services_requests_pg.flash.message,
                "VM Provision Request was Submitted, you will be notified when your VMs are ready")
        services_requests_pg.approve_request(1)

def assert_vm_state(provisioning_data, current_page, current_state):
    ''' Asserts that the VM is created in the expected state '''
    vm_pg = current_page.header.site_navigation_menu(
            'Services').sub_navigation_menu('Virtual Machines').click()
    sleep(180)
    vm_pg.refresh()
    vm_pg.wait_for_vm_state_change(provisioning_data["vm_name"], 'on', 12)
    Assert.equal(vm_pg.quadicon_region.get_quadicon_by_title(
        provisioning_data["vm_name"]).current_state, current_state,
        "vm not in correct state: " + current_state)
    return vm_pg

def remove_vm(provisioning_data, current_page, provider_api_clients):
    '''Powers off and removes the VM'''
    vm_pg = current_page.header.site_navigation_menu(
            'Services').sub_navigation_menu('Virtual Machines').click()
    vm_pg.power_off([provisioning_data["vm_name"]])
    Assert.true(vm_pg.flash.message.startswith("Stop initiated"))
    vm_pg.wait_for_vm_state_change(provisioning_data["vm_name"], 'off', 12)
    Assert.equal(vm_pg.quadicon_region.get_quadicon_by_title(
            provisioning_data["vm_name"]).current_state, 'off',
            "vm running")
    for provider in provider_api_clients.values():
        if (provisioning_data["vm_name"] + "/" +
                provisioning_data["vm_name"] + ".vmx"
                ) in provider.list_vm() or provisioning_data["vm_name"] \
                        in provider.list_vm():
            provider.delete_vm(provisioning_data["vm_name"])

