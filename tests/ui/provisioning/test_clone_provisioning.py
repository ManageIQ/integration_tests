# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest
from unittestzero import Assert
from fixtures.server_roles import default_roles, server_roles
from tests.ui.provisioning.test_base_provisioning import TestBaseProvisioning

@pytest.mark.nondestructive
@pytest.mark.fixtureconf(server_roles=default_roles+('automate',))
@pytest.mark.usefixtures(
    "maximized",
    "setup_infrastructure_providers",
    "setup_auto_placement_host",
    "setup_auto_placement_datastore",
    "mgmt_sys_api_clients",
    "setup_soap_create_vm")
class TestCloneProvisioning(TestBaseProvisioning):

    def test_clone_vm_to_vm(
            self,
            infra_vms_pg,
            provisioning_data_basic_only,
            vmware_linux_setup_data,
            mgmt_sys_api_clients,
            random_name):
        '''Test Cloning VM to VM'''
        provision_pg = infra_vms_pg.click_on_clone_items(
            vmware_linux_setup_data['vm_name'])
        self.complete_provision_pages_info(provisioning_data_basic_only,
            provision_pg, random_name)
        vm_pg = self.assert_vm_state(provisioning_data_basic_only,
            provision_pg, "on", random_name)
        self.teardown_remove_first_vm(mgmt_sys_api_clients,
            vmware_linux_setup_data)
        self.remove_vm(provisioning_data_basic_only, vm_pg, \
            mgmt_sys_api_clients, random_name)

