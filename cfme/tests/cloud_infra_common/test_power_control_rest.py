# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.common.vm import VM
from utils import testgen
from utils.generators import random_vm_name
from utils.wait import wait_for
from utils.log import logger
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.ec2 import EC2Provider


pytestmark = [
    test_requirements.power,
    pytest.mark.usefixtures('uses_infra_providers', 'uses_cloud_providers'),
    pytest.mark.tier(2)
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.all_providers(metafunc)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture(scope="module")
def vm_obj(request, provider, setup_provider_modscope, small_template_modscope):
    vm_obj = VM.factory(random_vm_name('pwrctl'), provider, template_name=small_template_modscope)

    @request.addfinalizer
    def _delete_vm():
        try:
            provider.mgmt.delete_vm(vm_obj.name)
        except Exception:
            logger.warning("Failed to delete vm `{}`.".format(vm_obj.name))

    vm_obj.create_on_provider(find_in_cfme=True, allow_skip="default")
    return vm_obj


def verify_vm_power_state(vm, state, num_sec=1000, action=None):
    if action:
        action(vm)
    wait_for(lambda: vm.power_state == state,
        num_sec=num_sec, delay=20, fail_func=vm.reload,
        message='Wait for VM state `{}` (current state: {})'.format(state, vm.power_state))


def verify_action_result(rest_api, assert_success=True):
    assert rest_api.response.status_code == 200
    response = rest_api.response.json()
    if 'results' in response:
        response = response['results'][0]
    message = response['message']
    success = response['success']
    if assert_success:
        assert success
    return success, message


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
    verify_vm_power_state(vm, state=vm_obj.STATE_ON,
        action=vm_obj.get_collection_via_rest().action.start)

    if from_detail:
        vm.action.stop()
    else:
        vm_obj.get_collection_via_rest().action.stop(vm)
    verify_action_result(rest_api)
    verify_vm_power_state(vm, state=vm_obj.STATE_OFF)


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
    # If vm is on, stop it. Otherwise try to start from whatever state it's currently in.
    if vm.power_state == vm_obj.STATE_ON:
        verify_vm_power_state(vm, state=vm_obj.STATE_OFF,
            action=vm_obj.get_collection_via_rest().action.stop)

    if from_detail:
        vm.action.start()
    else:
        vm_obj.get_collection_via_rest().action.start(vm)
    verify_action_result(rest_api)
    verify_vm_power_state(vm, state=vm_obj.STATE_ON)


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
    verify_vm_power_state(vm, state=vm_obj.STATE_ON,
        action=vm_obj.get_collection_via_rest().action.start)

    if from_detail:
        vm.action.suspend()
    else:
        vm_obj.get_collection_via_rest().action.suspend(vm)
    success, message = verify_action_result(rest_api, assert_success=False)
    if isinstance(vm_obj.provider, GCEProvider) or isinstance(vm_obj.provider, EC2Provider):
        assert success is False
        assert "not available" in message
    else:
        assert success
        verify_vm_power_state(vm, state=vm_obj.STATE_SUSPENDED)


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
    verify_vm_power_state(vm, state=vm_obj.STATE_ON,
        action=vm_obj.get_collection_via_rest().action.start)

    old_date = vm.updated_on
    if from_detail:
        vm.action.reset()
    else:
        vm_obj.get_collection_via_rest().action.reset(vm)
    success, message = verify_action_result(rest_api, assert_success=False)
    if isinstance(vm_obj.provider, GCEProvider) or isinstance(vm_obj.provider, EC2Provider):
        assert success is False
        assert "not available" in message
    else:
        assert success
        wait_for(lambda: vm.updated_on >= old_date,
            num_sec=600, delay=20, fail_func=vm.reload, message='Wait for VM to reset')
