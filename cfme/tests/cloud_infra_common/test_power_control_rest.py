# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.vm import VM
from utils import testgen
from utils.version import current_version
from utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures('uses_infra_providers', 'uses_cloud_providers')
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.all_providers(
        metafunc, 'small_template', template_location=["small_template"])

    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture(scope="function")
def vm_obj(request, provider, setup_provider, small_template, rest_api):
    vm_obj = VM.factory(
        'test_pwrctl_{}'.format(fauxfactory.gen_alpha(length=8).lower()),
        provider, template_name=small_template)

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
    lambda provider: provider.category == 'cloud' and current_version() <= "5.5.2.4")
@pytest.mark.parametrize("from_detail", [True, False], ids=["cfrom_detail", "from_collection"])
def test_stop(rest_api, vm_obj, from_detail):
    vm = vm_obj.get_vm_via_rest()
    assert "stop" in vm.action
    verify_vm_power_state(vm, state=vm_obj.STATE_ON)
    if from_detail:
        vm.action.stop()
    else:
        rest_api.collections.vms.action.stop(vm)
    wait_for(lambda: vm .power_state == vm_obj.STATE_OFF,
        num_sec=1000, delay=20, fail_func=vm.reload,
        message='Wait for VM to stop (current state: {})'.format(vm.power_state))


@pytest.mark.uncollectif(
    lambda provider: provider.category == 'cloud' and current_version() <= "5.5.2.4")
@pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
def test_start(rest_api, vm_obj, from_detail):
    vm = vm_obj.get_vm_via_rest()
    assert "start" in vm.action
    verify_vm_power_state(vm, state=vm_obj.STATE_SUSPENDED,
        action=rest_api.collections.vms.action.suspend)
    vm.action.start()
    wait_for(lambda: vm .power_state == vm_obj.STATE_ON,
        num_sec=1000, delay=20, fail_func=vm.reload,
        message='Wait for VM to stop (current state: {})'.format(vm.power_state))


@pytest.mark.uncollectif(
    lambda provider: provider.category == 'cloud' and current_version() <= "5.5.2.4")
@pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
def test_suspend(rest_api, vm_obj, from_detail):
    vm = vm_obj.get_vm_via_rest()
    assert "suspend" in vm.action
    verify_vm_power_state(vm, state=vm_obj.STATE_ON)
    vm.action.suspend()
    wait_for(lambda: vm .power_state == vm_obj.STATE_SUSPENDED,
        num_sec=1000, delay=20, fail_func=vm.reload,
        message='Wait for VM to stop (current state: {})'.format(vm.power_state))
