# -*- coding: utf-8 -*-

import fauxfactory
import pytest

from cfme.configure import configuration as config
from cfme.cloud import provider as cloud_provider
from cfme.infrastructure.provider import wait_for_a_provider
from cfme.infrastructure.virtual_machines import Vm
from fixtures.pytest_store import store
from utils.appliance import provision_appliance
from utils.log import logger
from utils.providers import setup_a_provider
from utils import version


def provision_vm(request, provider_crud, provider_mgmt):
    """Function to provision appliance to the provider being tested"""
    vm_name = "test_rest_db_" + fauxfactory.gen_alphanumeric()
    vm = Vm(vm_name, provider_crud)

    request.addfinalizer(vm.delete_from_provider)

    if not provider_mgmt.does_vm_exist(vm_name):
        logger.info("deploying {} on provider {}".format(vm_name, provider_crud.key))
        vm.create_on_provider(allow_skip="default")
    else:
        logger.info("recycling deployed vm {} on provider {}".format(vm_name, provider_crud.key))
    vm.provider_crud.refresh_provider_relationships()
    vm.wait_to_appear()
    return vm


@pytest.fixture(scope="module")
def get_appliances():
    """Returns two database-owning appliances

    """
    ver_to_prov = str(version.current_version())
    appl1 = provision_appliance(ver_to_prov, 'test_back')
    appl2 = provision_appliance(ver_to_prov, 'test_rest')
    appl1.configure(region=0, patch_ajax_wait=False)
    appl1.ipapp.wait_for_web_ui()
    appl2.configure(region=0, patch_ajax_wait=False)
    appl2.ipapp.wait_for_web_ui()
    return (appl1, appl2)


@pytest.mark.uncollectif(
    lambda: not (store.current_appliance.is_downstream and
        store.current_appliance.version >= '5.4'))
def test_db_restore(request, soft_assert):

    appl1, appl2 = get_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)

    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        # Manage infra,cloud providers and set some roles before taking a DB backup
        config.set_server_roles(automate=True)
        roles = config.get_server_roles()
        provider_crud = setup_a_provider('infra', 'virtualcenter', validate=True)
        provider_mgmt = provider_crud.get_mgmt_system()
        wait_for_a_provider()
        setup_a_provider('cloud', 'ec2', validate=True)
        cloud_provider.wait_for_a_provider()

        providers_appl1 = appl1.ipapp.managed_providers
        appl1.ipapp.backup_database()

    # Fetch v2_key and DB backup from the first appliance
    with appl1.ipapp.ssh_client as ssh:
        rand_filename = "/tmp/v2_key_{}".format(fauxfactory.gen_alphanumeric())
        ssh.get_file("/var/www/miq/vmdb/certs/v2_key", rand_filename)
        dump_filename = "/tmp/db_dump_{}".format(fauxfactory.gen_alphanumeric())
        ssh.get_file("/tmp/evm_db.backup", dump_filename)

    with appl2.ipapp.ssh_client as ssh:
        ssh.put_file(rand_filename, "/var/www/miq/vmdb/certs/v2_key")
        ssh.put_file(dump_filename, "/tmp/evm_db.backup")

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        # Restore DB on the second appliance
        appl2.ipapp.restore_database()
        appl2.ipapp.wait_for_web_ui()
        wait_for_a_provider()
        cloud_provider.wait_for_a_provider()

        # Assert providers on the second appliance
        providers_appl2 = appl2.ipapp.managed_providers
        assert set(providers_appl2).issubset(providers_appl1),\
            'Restored DB is missing some providers'

        # Verify that existing provider can detect new VMs on the second appliance
        vm = provision_vm(request, provider_crud, provider_mgmt)
        soft_assert(vm.find_quadicon().state == 'currentstate-on')
        soft_assert(vm.provider_crud.get_mgmt_system().is_vm_running(vm.name),
            "vm running")

        # Assert server roles on the second appliance
        for role, is_enabled in config.get_server_roles(db=False).iteritems():
            if is_enabled:
                assert roles[role], "Role '%s' is selected but should not be" % role
            else:
                assert not roles[role], "Role '%s' is not selected but should be" % role
