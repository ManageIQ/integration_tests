# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest
import time
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
    #"setup_retirement_policies",
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
        '''Test Retiring a VM'''
        infra_vms_pg.add_policy_profile(
            vmware_linux_setup_data['vm_name'],
            vmware_linux_setup_data['policy_profile'])
        infra_vms_pg.click_on_retire_items(vmware_linux_setup_data['vm_name'])
        # Poll for the VM to be removed from the Provider
        self.wait_for_vm_removed_from_provider(
            db_session,
            soap_client,
            mgmt_sys_api_clients[vmware_linux_setup_data["provider_key"]],
            vmware_linux_setup_data,
            12)

    def wait_for_vm_removed_from_provider(
            self,
            db_session,
            soap_client,
            provider,
            vmware_linux_setup_data,
            timeout_in_minutes):
        ''' Poll for VM to be removed from provider'''
        minute_count = 0
        while (minute_count < timeout_in_minutes):
            if not (vmware_linux_setup_data["vm_name"] + "/" +
                    vmware_linux_setup_data["vm_name"] + ".vmx") \
                    in provider.list_vm() and \
                not vmware_linux_setup_data["vm_name"] \
                    in provider.list_vm():
                break
            print "Sleeping 60 seconds, iteration " + str(minute_count + 1) + \
                " of " + str(timeout_in_minutes)
            time.sleep(60)
            minute_count += 1
            if (minute_count == timeout_in_minutes) and \
                    not (
                        vmware_linux_setup_data["vm_name"] + "/" +
                        vmware_linux_setup_data["vm_name"] + ".vmx") \
                    in provider.list_vm() and \
                    not vmware_linux_setup_data["vm_name"] \
                    in provider.list_vm():
                raise Exception(
                    "timeout reached(" + str(timeout_in_minutes) +
                    " minutes) before vm removed from provider.")
