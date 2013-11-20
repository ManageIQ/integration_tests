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
    "mgmt_sys_api_clients",
    "db_session",
    "soap_client")


class TestTemplateProvisioning(TestBaseProvisioning):
    def test_linux_template_cancel(
            self,
            provisioning_start_page,
            provisioning_data_basic_only):
        '''Test Cancel button'''
        provisioning_start_page.click_on_template_item(
            provisioning_data_basic_only["template"],
            provisioning_data_basic_only["provider"])
        provision_pg = provisioning_start_page.click_on_continue()
        vm_pg = provision_pg.click_on_cancel()
        Assert.true(vm_pg.is_the_current_page,
                "not returned to the correct page")

    def test_linux_template_workflow(
            self,
            server_roles,
            default_roles_list,
            provisioning_start_page,
            provisioning_data_basic_only,
            mgmt_sys_api_clients,
            random_name,
            db_session,
            soap_client):
        '''Test Basic Provisioning Workflow'''
        provisioning_start_page.click_on_template_item(
            provisioning_data_basic_only["template"],
            provisioning_data_basic_only["provider"])
        provision_pg = provisioning_start_page.click_on_continue()
        self.complete_provision_pages_info(provisioning_data_basic_only,
            provision_pg, random_name)
        self.assert_vm_state(provisioning_data_basic_only, provision_pg,
            "on", random_name)
        self.teardown_remove_from_provider(db_session, soap_client,
            mgmt_sys_api_clients,
            '%s%s' % (provisioning_data_basic_only["vm_name"], random_name))
