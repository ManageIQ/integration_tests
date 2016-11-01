# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.common.vm import VM
from utils import testgen
from utils.generators import random_vm_name
from utils.version import current_version
from utils.wait import wait_for


pytestmark = [
    test_requirements.power,
    pytest.mark.usefixtures('uses_infra_providers', 'uses_cloud_providers'),
    pytest.mark.tier(2)
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.all_providers(metafunc)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture(scope="function")
def vm_obj(request, provider, setup_provider, small_template, rest_api):
    vm_obj = VM.factory(random_vm_name('pwrctl'), provider, template_name=small_template)

    @request.addfinalizer
    def _delete_vm():
        if provider.mgmt.does_vm_exist(vm_obj.name):
            provider.mgmt.delete_vm(vm_obj.name)
    vm_obj.create_on_provider(find_in_cfme=True, allow_skip="default")
    return vm_obj


def verify_vm_power_state(vm, state, minutes=10, action=None):
    if action:
        action(vm)
    wait_for(lambda: vm.power_state == state,
        num_sec=minutes * 60, delay=20, fail_func=vm.reload,
        message='Wait for VM to {} (current state: {})'.format(state, vm.power_state))


@pytest.mark.uncollectif(
    lambda provider: provider.category == 'cloud' and current_version() < "5.6.0")
@pytest.mark.parametrize("from_detail", [True, False], ids=["cfrom_detail", "from_collection"])
def test_stop(rest_api, vm_obj, from_detail):
    """Test stop of vm

    Prerequisities:

        * An appliance with ``/api`` available.
        * VM

    Steps:

        * POST /api/vms/<id> (method ``stop``)
        OR
        * POST /api/vms (method ``stop``) with ``href`` of the vm or vms

    Metadata:
        test_flag: rest
    """
    vm = vm_obj.get_vm_via_rest()
    assert "stop" in vm.action
    verify_vm_power_state(vm, state=vm_obj.STATE_ON)
    if from_detail:
        vm.action.stop()
    else:
        vm_obj.get_collection_via_rest().action.stop(vm)
    wait_for(lambda: vm.power_state == vm_obj.STATE_OFF,
        num_sec=1000, delay=20, fail_func=vm.reload,
        message='Wait for VM to stop (current state: {})'.format(vm.power_state))


@pytest.mark.uncollectif(
    lambda provider: provider.category == 'cloud' and current_version() < "5.6.0")
@pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
def test_start(rest_api, vm_obj, from_detail):
    """Test start vm

    Prerequisities:

        * An appliance with ``/api`` available.
        * VM

    Steps:

        * POST /api/vms/<id> (method ``start``)
        OR
        * POST /api/vms (method ``start``) with ``href`` of the vm or vms

    Metadata:
        test_flag: rest
    """
    vm = vm_obj.get_vm_via_rest()
    assert "start" in vm.action
    verify_vm_power_state(vm, state=vm_obj.STATE_SUSPENDED,
        action=vm_obj.get_collection_via_rest().action.suspend)
    if from_detail:
        vm.action.start()
    else:
        vm_obj.get_collection_via_rest().action.start(vm)
    wait_for(lambda: vm.power_state == vm_obj.STATE_ON,
        num_sec=1000, delay=20, fail_func=vm.reload,
        message='Wait for VM to stop (current state: {})'.format(vm.power_state))


@pytest.mark.uncollectif(
    lambda provider: provider.category == 'cloud' and current_version() < "5.6.0")
@pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
def test_suspend(rest_api, vm_obj, from_detail):
    """Test suspend vm

    Prerequisities:

        * An appliance with ``/api`` available.
        * VM

    Steps:

        * POST /api/vms/<id> (method ``suspend``)
        OR
        * POST /api/vms (method ``suspend``) with ``href`` of the vm or vms

    Metadata:
        test_flag: rest
    """
    vm = vm_obj.get_vm_via_rest()
    assert "suspend" in vm.action
    verify_vm_power_state(vm, state=vm_obj.STATE_ON)
    if from_detail:
        vm.action.suspend()
    else:
        vm_obj.get_collection_via_rest().action.suspend(vm)
    wait_for(lambda: vm.power_state == vm_obj.STATE_SUSPENDED,
        num_sec=1000, delay=20, fail_func=vm.reload,
        message='Wait for VM to stop (current state: {})'.format(vm.power_state))


@pytest.mark.uncollectif(lambda: current_version() < "5.6.0")
@pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
def test_reset_vm(rest_api, vm_obj, from_detail):
    """
    Test reset vm

    Prerequisities:

        * An appliance with ``/api`` available.
        * VM

    Steps:

        * POST /api/vms/<id> (method ``reset``)
        OR
        * POST /api/vms (method ``reset``) with ``href`` of the vm or vms

    Metadata:
        test_flag: rest
    """
    vm = vm_obj.get_vm_via_rest()
    assert "reset" in vm.action
    verify_vm_power_state(vm, state=vm_obj.STATE_ON)
    old_date = vm.updated_on
    if from_detail:
        vm.action.reset()
    else:
        vm_obj.get_collection_via_rest().action.reset(vm)
    wait_for(lambda: vm.updated_on >= old_date,
        num_sec=600, delay=20, fail_func=vm.reload, message='Wait for VM to reset')
