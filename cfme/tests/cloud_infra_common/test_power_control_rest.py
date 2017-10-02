# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.common.vm import VM
from cfme.utils import testgen
from cfme.utils.generators import random_vm_name
from cfme.utils.wait import wait_for
from cfme.utils.log import logger
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider


pytestmark = [
    test_requirements.power,
    pytest.mark.usefixtures('uses_infra_providers', 'uses_cloud_providers'),
    pytest.mark.tier(2)
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.all_providers(metafunc)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture(scope='function')
def vm_name():
    return random_vm_name('pwrctl')


@pytest.fixture(scope="function")
def vm_obj(request, provider, setup_provider, small_template, vm_name):
    vm_obj = VM.factory(vm_name, provider, template_name=small_template.name)

    @request.addfinalizer
    def _delete_vm():
        try:
            provider.mgmt.delete_vm(vm_obj.name)
        except Exception:
            logger.warning("Failed to delete vm `{}`.".format(vm_obj.name))

    vm_obj.create_on_provider(timeout=2400, find_in_cfme=True, allow_skip="default")
    return vm_obj


def wait_for_vm_state_change(vm_obj, state):
    vm = vm_obj.get_vm_via_rest()
    if vm_obj.provider.one_of(GCEProvider, EC2Provider, SCVMMProvider):
        num_sec = 4000  # extra time for slow providers
    else:
        num_sec = 1200

    def _state_changed():
        vm.reload()
        return vm.power_state == state
    wait_for(_state_changed, num_sec=num_sec, delay=45, silent_failure=True,
        message="Wait for VM state `{}` (current state: {})".format(state, vm.power_state))


def verify_vm_power_state(vm, state):
    vm.reload()
    return vm.power_state == state


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
def test_stop_vm_rest(appliance, vm_obj, verify_vm_running, soft_assert, from_detail):
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
    rest_api = appliance.rest_api
    vm_obj.wait_for_vm_state_change(desired_state=vm_obj.STATE_ON)
    vm = rest_api.collections.vms.get(name=vm_obj.name)

    if from_detail:
        vm.action.stop()
    else:
        rest_api.collections.vms.action.stop(vm)
    verify_action_result(rest_api)
    wait_for_vm_state_change(vm_obj, vm_obj.STATE_OFF)
    soft_assert(not verify_vm_power_state(vm, vm_obj.STATE_ON), "vm still running")


@pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
def test_start_vm_rest(appliance, vm_obj, verify_vm_stopped, soft_assert, from_detail):
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
    rest_api = appliance.rest_api
    vm_obj.wait_for_vm_state_change(desired_state=vm_obj.STATE_OFF, timeout=1200)
    vm = rest_api.collections.vms.get(name=vm_obj.name)

    if from_detail:
        vm.action.start()
    else:
        rest_api.collections.vms.action.start(vm)
    verify_action_result(rest_api)
    wait_for_vm_state_change(vm_obj, vm_obj.STATE_ON)
    soft_assert(verify_vm_power_state(vm, vm_obj.STATE_ON), "vm not running")


@pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
def test_suspend_vm_rest(appliance, vm_obj, verify_vm_running, soft_assert, from_detail):
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
    rest_api = appliance.rest_api
    vm_obj.wait_for_vm_state_change(desired_state=vm_obj.STATE_ON)
    vm = rest_api.collections.vms.get(name=vm_obj.name)

    if from_detail:
        vm.action.suspend()
    else:
        rest_api.collections.vms.action.suspend(vm)
    success, message = verify_action_result(rest_api, assert_success=False)
    if vm_obj.provider.one_of(GCEProvider, EC2Provider):
        assert success is False
        assert "not available" in message
    else:
        assert success
        wait_for_vm_state_change(vm_obj, vm_obj.STATE_SUSPENDED)
        soft_assert(verify_vm_power_state(vm, vm_obj.STATE_SUSPENDED), "vm not suspended")


@pytest.mark.uncollectif(lambda provider: provider.one_of(RHEVMProvider),
                         reason='Not supported for RHV provider')
@pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
def test_reset_vm_rest(vm_obj, verify_vm_running, from_detail, appliance):
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
    rest_api = appliance.rest_api
    vm_obj.wait_for_vm_state_change(desired_state=vm_obj.STATE_ON)
    vm = rest_api.collections.vms.get(name=vm_obj.name)

    old_date = vm.updated_on
    if from_detail:
        vm.action.reset()
    else:
        rest_api.collections.vms.action.reset(vm)
    success, message = verify_action_result(rest_api, assert_success=False)
    if appliance.version < '5.7':
        unsupported_providers = (GCEProvider, EC2Provider, SCVMMProvider)
    else:
        unsupported_providers = (GCEProvider, EC2Provider)
    if vm_obj.provider.one_of(*unsupported_providers):
        assert success is False
        assert "not available" in message
    else:
        assert success
        wait_for(lambda: vm.updated_on >= old_date,
            num_sec=600, delay=20, fail_func=vm.reload, message='Wait for VM to reset')
