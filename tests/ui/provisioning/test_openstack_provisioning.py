# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest
from tests.ui.provisioning.test_base_provisioning import TestBaseProvisioning


@pytest.mark.nondestructive
@pytest.mark.fixtureconf(server_roles="+automate")
@pytest.mark.usefixtures(
    "maximized",
    "setup_cloud_providers",
    "mgmt_sys_api_clients",
    "server_roles",
    "db_session",
    "soap_client")
class TestImageProvisioning(TestBaseProvisioning):
    def test_openstack_image_workflow(
            self,
            providers_data,
            inst_provisioning_start_page,
            openstack_provisioning_data,
            mgmt_sys_api_clients,
            random_name,
            db_session,
            soap_client):
        '''Test Basic Provisioning Workflow'''
        inst_provisioning_start_page.click_on_template_item(
            openstack_provisioning_data["image"],
            providers_data[openstack_provisioning_data["provider_key"]]["name"])
        provision_pg = inst_provisioning_start_page.click_on_continue()
        self.complete_provision_pages_info(
            openstack_provisioning_data,
            provision_pg,
            random_name)
        self.assert_vm_state(
            openstack_provisioning_data, provision_pg, "on", random_name)
        self.teardown_remove_from_provider(
            db_session, soap_client,
            mgmt_sys_api_clients[openstack_provisioning_data["provider_key"]],
            '%s%s' % (openstack_provisioning_data["vm_name"], random_name))
