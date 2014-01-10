# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest
from tests.ui.provisioning.test_base_provisioning import TestBaseProvisioning
from utils.wait import wait_for


@pytest.mark.fixtureconf(server_roles="+automate")
@pytest.mark.usefixtures(
    "server_roles",
    "setup_infrastructure_providers",
    "setup_auto_placement_host",
    "setup_auto_placement_datastore",
    "mgmt_sys_api_clients",
    "setup_soap_create_vm",
    "setup_retirement_policies",
    "db_session",
    "soap_client")
class TestVmRetirement(TestBaseProvisioning):
    def test_vm_retire_delete(
            self,
            infra_vms_pg,
            vmware_linux_setup_data,
            mgmt_sys_api_clients,
            db_session,
            soap_client):
        """ Test Retiring a VM

        """
        infra_vms_pg.find_vm_page(vmware_linux_setup_data['vm_name'], None, False)
        infra_vms_pg.add_policy_profile(
            [vmware_linux_setup_data['vm_name']],
            vmware_linux_setup_data['policy_profile'])
        infra_vms_pg.click_on_retire_items(vmware_linux_setup_data['vm_name'])
        # Poll for the VM to be removed from the Provider
        wait_for(lambda provider, setup_data: setup_data["vm_name"] not in provider.list_vm(),
                 mgmt_sys_api_clients[vmware_linux_setup_data["provider_key"]],
                 vmware_linux_setup_data,
                 num_sec=12 * 60)
