# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest
from unittestzero import Assert
from tests.ui.provisioning.test_base_provisioning import TestBaseProvisioning

@pytest.mark.nondestructive
@pytest.mark.fixtureconf(server_roles="+automate")
@pytest.mark.usefixtures(
        "maximized",
        "setup_infrastructure_providers",
        "setup_pxe_provision",
        "mgmt_sys_api_clients")
class TestTemplateProvisioning(TestBaseProvisioning):
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
            default_roles_list,
            provisioning_start_page,
            provisioning_data,
            mgmt_sys_api_clients,
            random_name):
        '''Test Basic Provisioning Workflow'''
        assert len(server_roles) == len(default_roles_list) + 1
        provisioning_start_page.click_on_template_item(
            provisioning_data["template"])
        provision_pg = provisioning_start_page.click_on_continue()
        self.complete_provision_pages_info(provisioning_data, provision_pg, \
            random_name)
        vm_pg = self.assert_vm_state(provisioning_data, provision_pg, "on", \
            random_name)
        self.remove_vm(provisioning_data, vm_pg, mgmt_sys_api_clients, \
            random_name)


