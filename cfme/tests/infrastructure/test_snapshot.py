# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.virtual_machines import Vm
from utils import testgen
from utils.conf import credentials
from utils.providers import setup_provider
from utils.log import logger
from utils.ssh import SSHClient
from utils.wait import wait_for


pytestmark = [pytest.mark.long_running]


pytest_generate_tests = testgen.generate(testgen.infra_providers, 'full_template', scope="module")


@pytest.fixture(scope="module")
def provider_init(provider_key):
    """cfme/infrastructure/provider.py provider object."""
    try:
        setup_provider(provider_key)
    except Exception as e:
        pytest.skip("Skipping,because it's not possible to set up this provider({})".format(str(e)))


@pytest.fixture(scope="module")
def vm_name():
    return "test_snpsht_" + fauxfactory.gen_alphanumeric()


@pytest.fixture(scope="module")
def test_vm(request, provider_init, provider_crud, provider_mgmt, provider_data, vm_name):
    """Fixture to provision appliance to the provider being tested if necessary"""
    vm = Vm(vm_name, provider_crud, template_name=provider_data['full_template']['name'])

    if not provider_mgmt.does_vm_exist(vm_name):
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    return vm


def new_snapshot(test_vm):
    new_snapshot = Vm.Snapshot(
        name="snpshot_" + fauxfactory.gen_alphanumeric(8),
        description="snapshot", memory=False, parent_vm=test_vm)
    return new_snapshot


@pytest.mark.uncollectif(lambda provider_type: provider_type != 'virtualcenter')
def test_snapshot_crud(test_vm, provider_key, provider_type):
    """Tests snapshot crud

    Metadata:
        test_flag: snapshot, provision
    """
    snapshot = new_snapshot(test_vm)
    snapshot.create()
    snapshot.delete()


@pytest.mark.uncollectif(lambda provider_type: provider_type != 'virtualcenter')
def test_delete_all_snapshots(test_vm, provider_key, provider_type):
    """Tests snapshot removal

    Metadata:
        test_flag: snapshot, provision
    """
    snapshot1 = new_snapshot(test_vm)
    snapshot1.create()
    snapshot2 = new_snapshot(test_vm)
    snapshot2.create()
    snapshot2.delete_all()


@pytest.mark.uncollectif(lambda provider_type: provider_type != 'virtualcenter')
def test_verify_revert_snapshot(test_vm, provider_key, provider_type, provider_data,
                                soft_assert, register_event, request):
    """Tests revert snapshot

    Metadata:
        test_flag: snapshot, provision
    """
    snapshot1 = new_snapshot(test_vm)
    ip = snapshot1.vm.provider_crud.get_mgmt_system().get_ip_address(snapshot1.vm.name)
    print ip
    ssh_kwargs = {
        'username': credentials[provider_data['full_template']['creds']]['username'],
        'password': credentials[provider_data['full_template']['creds']]['password'],
        'hostname': ip
    }
    ssh = SSHClient(**ssh_kwargs)
    ssh.run_command('touch snapshot1.txt')
    snapshot1.create()
    ssh.run_command('touch snapshot2.txt')
    snapshot2 = new_snapshot(test_vm)
    snapshot2.create()
    snapshot1.revert_to()
    # Wait for the snapshot to become active
    logger.info('Waiting for vm %s to become active', snapshot1.name)
    wait_for(snapshot1.wait_for_snapshot_active, num_sec=300, delay=20, fail_func=sel.refresh)
    test_vm.wait_for_vm_state_change(desired_state=Vm.STATE_OFF, timeout=720)
    register_event(
        test_vm.provider_crud.get_yaml_data()['type'],
        "vm", test_vm.name, ["vm_power_on_req", "vm_power_on"])
    test_vm.power_control_from_cfme(option=Vm.POWER_ON, cancel=False)
    pytest.sel.force_navigate(
        'infrastructure_provider', context={'provider': test_vm.provider_crud})
    test_vm.wait_for_vm_state_change(desired_state=Vm.STATE_ON, timeout=900)
    soft_assert(test_vm.find_quadicon().state == 'currentstate-on')
    soft_assert(
        test_vm.provider_crud.get_mgmt_system().is_vm_running(test_vm.name), "vm not running")
    client = SSHClient(**ssh_kwargs)
    request.addfinalizer(test_vm.delete_from_provider)
    try:
        wait_for(lambda: client.run_command('test -e snapshot2.txt')[1] == 0, fail_condition=False)
        logger.info('Revert to snapshot %s successful', snapshot1.name)
    except:
        logger.info('Revert to snapshot %s Failed', snapshot1.name)
