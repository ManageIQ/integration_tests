# -*- coding: utf-8 -*-
import pytest

from cfme.common.vm import VM
from cfme.exceptions import CFMEException
from cfme.utils import ports
from cfme.utils.generators import random_vm_name
from cfme.utils.net import net_check
from cfme.utils.wait import wait_for


def _create_vm(request, template, provider, vm_name):
    vm_obj = VM.factory(vm_name, provider, template_name=template.name)
    vm_obj.create_on_provider(allow_skip="default")
    provider.mgmt.start_vm(vm_obj.name)
    provider.mgmt.wait_vm_running(vm_obj.name)
    # In order to have seamless SSH connection
    vm_ip, _ = wait_for(
        provider.mgmt.current_ip_address, func_args=[vm_obj.name],
        num_sec=300, delay=5, fail_condition={None}, message="wait for testing VM IP address.")
    wait_for(
        net_check, func_args=[ports.SSH, vm_ip], func_kwargs={"force": True},
        num_sec=300, delay=5, message="testing VM's SSH available")
    if not vm_obj.exists:
        provider.refresh_provider_relationships()
        vm_obj.wait_to_appear()

    @request.addfinalizer
    def _cleanup():
        vm_obj.cleanup_on_provider()
        provider.refresh_provider_relationships()

    return vm_obj


def _get_vm_name(request):
    """Helper function to get vm name from test requirement mark.

    At first we try to get a requirement value from ``pytestmark`` module list. If it's missing we
    can try to look up it in the test function itself. There is one restriction for it. We cannot
    get the test function mark from module scoped fixtures.
    """
    req = [mark.args[0] for mark in request.module.pytestmark if mark.name == "requirement"]
    if not req and request.scope == "function":
        try:
            req = request.function.requirement.args
        except AttributeError:
            raise CFMEException("VM name can not be obtained")
    return random_vm_name(req[0])


@pytest.fixture(scope="module")
def full_template_vm_modscope(request, full_template_modscope, provider, setup_provider_modscope):
    vm_name = _get_vm_name(request)
    return _create_vm(request, full_template_modscope, provider, vm_name)


@pytest.fixture(scope="function")
def full_template_vm(request, full_template, provider, setup_provider):
    vm_name = _get_vm_name(request)
    return _create_vm(request, full_template, provider, vm_name)
