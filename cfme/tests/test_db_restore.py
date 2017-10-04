# -*- coding: utf-8 -*-

import fauxfactory
import pytest

from cfme.cloud import provider as cloud_provider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.common.vm import VM
from cfme.infrastructure.provider import wait_for_a_provider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from fixtures.pytest_store import store
from cfme.utils.appliance import provision_appliance
from cfme.utils.log import logger
from cfme.utils.providers import list_providers_by_class
from cfme.utils import version


@pytest.fixture
def virtualcenter_provider_crud():
    try:
        return list_providers_by_class(VMwareProvider)[0]
    except IndexError:
        pytest.skip("No VMware providers available (required)")


@pytest.fixture
def ec2_provider_crud():
    try:
        return list_providers_by_class(EC2Provider)[0]
    except IndexError:
        pytest.skip("No EC2 provider available (required)")


def provision_vm(request, provider):
    """Function to provision appliance to the provider being tested"""
    vm_name = "test_rest_db_" + fauxfactory.gen_alphanumeric()
    vm = VM.factory(vm_name, provider)

    request.addfinalizer(vm.delete_from_provider)

    if not provider.mgmt.does_vm_exist(vm_name):
        logger.info("deploying %s on provider %s", vm_name, provider.key)
        vm.create_on_provider(allow_skip="default")
    else:
        logger.info("recycling deployed vm %s on provider %s", vm_name, provider.key)
    vm.provider.refresh_provider_relationships()
    vm.wait_to_appear()
    return vm


@pytest.fixture(scope="module")
def get_appliances():
    """Returns two database-owning appliances

    """
    ver_to_prov = str(version.current_version())
    appl1 = provision_appliance(ver_to_prov, 'test_back')
    appl2 = provision_appliance(ver_to_prov, 'test_rest')
    appl1.configure(region=0)
    appl1.ipapp.wait_for_web_ui()
    appl2.configure(region=0)
    appl2.ipapp.wait_for_web_ui()
    return (appl1, appl2)


@pytest.mark.tier(2)
@pytest.mark.uncollectif(
    lambda: not store.current_appliance.is_downstream)
def test_db_restore(request, soft_assert, virtualcenter_provider_crud, ec2_provider_crud,
                    appliance):

    appl1, appl2 = get_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)

    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        # Manage infra,cloud providers and set some roles before taking a DB backup
        server_info = appliance.server.settings
        server_info.enable_server_roles('automate')
        roles = server_info.server_roles_db
        virtualcenter_provider_crud.setup()
        wait_for_a_provider()
        ec2_provider_crud.setup()
        cloud_provider.wait_for_a_provider()

        providers_appl1 = appl1.ipapp.managed_known_providers
        appl1.ipapp.db.backup()

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
        appl2.ipapp.evmserverd.stop()
        appl2.ipapp.db.drop()
        appl2.ipapp.db.restore()
        appl2.ipapp.start_evm_service()
        appl2.ipapp.wait_for_web_ui()
        wait_for_a_provider()
        cloud_provider.wait_for_a_provider()

        # Assert providers on the second appliance
        providers_appl2 = appl2.ipapp.managed_known_providers
        assert set(providers_appl2).issubset(providers_appl1), (
            'Restored DB is missing some providers'
        )

        # Verify that existing provider can detect new VMs on the second appliance
        vm = provision_vm(request, virtualcenter_provider_crud)
        soft_assert(vm.find_quadicon().data['state'] == 'currentstate-on')
        soft_assert(vm.provider.mgmt.is_vm_running(vm.name), "vm running")

        # Assert server roles on the second appliance
        for role, is_enabled in server_info.server_roles_ui.iteritems():
            if is_enabled:
                assert roles[role], "Role '{}' is selected but should not be".format(role)
            else:
                assert not roles[role], "Role '{}' is not selected but should be".format(role)
