# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest
from unittestzero import Assert
from fixtures.server_roles import default_roles, server_roles

@pytest.mark.nondestructive
@pytest.mark.fixtureconf(server_roles=default_roles+('automate',))
@pytest.mark.usefixtures(
        "maximized",
        "setup_infrastructure_providers",
        "setup_pxe_provision",
        "mgmt_sys_api_clients")
class TestTemplateProvisioning:
    def test_linux_template_cancel(
            self,
            provisioning_start_page,
            provisioning_data_basic_only):
        '''Test Cancel button'''
        provisioning_start_page.click_on_template_item(
                provisioning_data_basic_only["template"])
        provision_pg = provisioning_start_page.click_on_continue()
        vm_pg = provision_pg.click_on_cancel()
        Assert.true(vm_pg.is_the_current_page,
                "not returned to the correct page")

    def test_linux_template_workflow(
            self,
            server_roles,
            provisioning_start_page,
            provisioning_data,
            mgmt_sys_api_clients,
            random_name):
        '''Test Basic Provisioning Workflow'''
        assert len(server_roles) == len(default_roles) + 1
        provisioning_start_page.click_on_template_item(
            provisioning_data["template"])
        provision_pg = provisioning_start_page.click_on_continue()
        self.complete_provision_pages_info(provisioning_data, provision_pg, \
            random_name)
        vm_pg = assert_vm_state(provisioning_data, provision_pg, "on", \
            random_name)
        remove_vm(provisioning_data, vm_pg, mgmt_sys_api_clients, \
            random_name)

    def complete_provision_pages_info(self,
        provisioning_data, provision_pg, random_name):
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
                provisioning_data["pxe_server"],
                provisioning_data["server_image"],
                str(provisioning_data["count"]),
                '%s%s' % (provisioning_data["vm_name"], random_name),
                provisioning_data["vm_description"])
        environment_pg = tab_buttons.tabbutton_by_name("Environment").click()
        environment_pg.fill_fields(
                unicode(provisioning_data["host"]),
                unicode(provisioning_data["datastore"]))
        hardware_pg = tab_buttons.tabbutton_by_name("Hardware").click()
        network_pg = tab_buttons.tabbutton_by_name("Network").click()
        if ("PXE" in provisioning_data["provision_type"]) or \
           ("ISO" in provisioning_data["provision_type"]):
            customize_pg = tab_buttons.tabbutton_by_name("Customize").click()
            customize_pg.fill_fields(
                provisioning_data["root_password"],
                provisioning_data["address_node_value"],
                provisioning_data["customization_template"])
        schedule_pg = tab_buttons.tabbutton_by_name("Schedule").click()
        schedule_pg.fill_fields(
                provisioning_data["when_to_provision"],
                provisioning_data["power_on"],
                str(provisioning_data["time_until_retirement"]))

        services_requests_pg = schedule_pg.click_on_submit()
        Assert.true(services_requests_pg.is_the_current_page,
                "not returned to the correct page")
        Assert.equal(services_requests_pg.flash_message,
                "VM Provision Request was Submitted, "\
                "you will be notified when your VMs are ready")
        services_requests_pg.approve_request(1)
        services_requests_pg.wait_for_request_status("Last 24 Hours", \
                "Finished", 12)

def assert_vm_state(provisioning_data, current_page, \
    current_state, random_name):
    ''' Asserts that the VM is created in the expected state '''
    vm_pg = current_page.header.site_navigation_menu(
            'Infrastructure').sub_navigation_menu('Virtual Machines').click()
    vm_pg.refresh()
    vm_pg.wait_for_vm_state_change( '%s%s' % (provisioning_data["vm_name"],
            random_name), 'on', 12)
    Assert.equal(vm_pg.quadicon_region.get_quadicon_by_title(
        '%s%s' % (provisioning_data["vm_name"], random_name))\
        .current_state, current_state,
        "vm not in correct state: " + current_state)
    return vm_pg

def remove_vm(provisioning_data,
    current_page, provider_api_clients, random_name):
    '''Powers off and removes the VM'''
    vm_pg = current_page.header.site_navigation_menu(
            'Infrastructure').sub_navigation_menu('Virtual Machines').click()
    vm_pg.power_off(['%s%s' % (provisioning_data["vm_name"], random_name)])
    Assert.true(vm_pg.flash.message.startswith("Stop initiated"))
    vm_pg.wait_for_vm_state_change(
            '%s%s' % (provisioning_data["vm_name"], random_name), 'off', 12)
    Assert.equal(vm_pg.quadicon_region.get_quadicon_by_title(
            '%s%s' % (provisioning_data["vm_name"], random_name))\
            .current_state, 'off', "vm running")
    for provider in provider_api_clients.values():
        if ('%s%s' % (provisioning_data["vm_name"], random_name) + "/" +
                '%s%s' % (provisioning_data["vm_name"], random_name) + ".vmx"
                ) in provider.list_vm() or \
                '%s%s' % (provisioning_data["vm_name"], random_name) \
                in provider.list_vm():
            provider.delete_vm('%s%s' % (provisioning_data["vm_name"], \
                random_name))

