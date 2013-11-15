# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest
import db
from unittestzero import Assert
from tests.ui.provisioning.test_base_provisioning import TestBaseProvisioning

@pytest.mark.nondestructive
@pytest.mark.fixtureconf(server_roles="+automate")
@pytest.mark.usefixtures(
    "maximized",
    "setup_infrastructure_providers",
    "setup_auto_placement_host",
    "setup_auto_placement_datastore",
    "mgmt_sys_api_clients",
    "setup_soap_create_vm",
    "db_session",
    "soap_client")

class TestVm2TemplateProvisioning(TestBaseProvisioning):
    def test_vm_to_template(
            self,
            infra_vms_pg,
            vmware_publish_to_template,
            vmware_linux_setup_data,
            mgmt_sys_api_clients,
            random_name,
            db_session,
            soap_client):
        '''Test Cloning VM to Template'''
        provision_pg = infra_vms_pg.click_on_publish_items(
            vmware_linux_setup_data['vm_name'])
        self.complete_provision_pages_info(vmware_publish_to_template,
            provision_pg, random_name)
        # Assert a template was created
        vm_pg = self.assert_vm_state(vmware_publish_to_template,
            provision_pg, "template", random_name)
        self.teardown_remove_from_provider(db_session, soap_client,
            mgmt_sys_api_clients, \
            '%s%s' % (vmware_publish_to_template["vm_name"], random_name))
        self.teardown_remove_from_provider(db_session, soap_client,
            mgmt_sys_api_clients, vmware_linux_setup_data["vm_name"])

