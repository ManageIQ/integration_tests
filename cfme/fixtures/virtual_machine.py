""" Fixtures ensuring that a VM/instance is in the specified state for the test
"""


import pytest
from cfme.common.vm import VM


def _get_vm_obj_if_exists_on_provider(provider, vm_name):
    vm = VM.factory(vm_name, provider)
    if not vm.does_vm_exist_on_provider():
        raise ValueError(
            "Unable to ensure VM state: "
            "VM '{}' does not exist on provider '{}'".format(vm_name, provider.key)
        )
    return vm


@pytest.fixture(scope="function")
def ensure_vm_running(provider, vm_name):
    """ Ensures that the VM/instance is in running state for the test

    Uses calls to the actual provider api; it will start the vm if necessary.

    Args:
        provider: Provider class object
        vm_name: Name of the VM/instance
    """
    vm = _get_vm_obj_if_exists_on_provider(provider, vm_name)
    return vm.ensure_state_on_provider(vm.STATE_ON)


@pytest.fixture(scope="function")
def ensure_vm_stopped(provider, vm_name):
    """ Ensures that the VM/instance is stopped for the test

    Uses calls to the actual provider api; it will stop the vm if necessary.

    Args:
        provider: Provider class object
        vm_name: Name of the VM/instance
    """
    vm = _get_vm_obj_if_exists_on_provider(provider, vm_name)
    return vm.ensure_state_on_provider(vm.STATE_OFF)

@pytest.fixture(scope="function")
def ensure_vm_suspended(provider, vm_name):
    """ Ensures that the VM/instance is suspended for the test

    Uses calls to the actual provider api; it will suspend the vm if necessary.

    Args:
        provider.mgmt: Provider class object
        vm_name: Name of the VM/instance
    """
    vm = _get_vm_obj_if_exists_on_provider(provider, vm_name)
    return vm.ensure_state_on_provider(vm.STATE_SUSPENDED)


@pytest.fixture(scope="function")
def ensure_vm_paused(provider, vm_name):
    """ Ensures that the VM/instance is paused for the test

    Uses calls to the actual provider api; it will pause the vm if necessary.

    Args:
        provider.mgmt: Provider class object
        vm_name: Name of the VM/instance
    """
    vm = _get_vm_obj_if_exists_on_provider(provider, vm_name)
    return vm.ensure_state_on_provider(vm.STATE_PAUSED)

