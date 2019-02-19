""" Fixtures ensuring that a VM/instance is in the specified state for the test
"""
import pytest
from wrapanapi import VmState


@pytest.fixture(scope="function")
def ensure_vm_running(provider, vm_name):
    """ Ensures that the VM/instance is in running state for the test

    Uses calls to the actual provider api; it will start the vm if necessary.

    Args:
        provider: Provider class object
        vm_name: Name of the VM/instance
    """
    return provider.mgmt.get_vm(vm_name).ensure_state(VmState.RUNNING)


@pytest.fixture(scope="function")
def ensure_vm_stopped(provider, vm_name):
    """ Ensures that the VM/instance is stopped for the test

    Uses calls to the actual provider api; it will stop the vm if necessary.

    Args:
        provider: Provider class object
        vm_name: Name of the VM/instance
    """
    return provider.mgmt.get_vm(vm_name).ensure_state(VmState.STOPPED)


@pytest.fixture(scope="function")
def ensure_vm_suspended(provider, vm_name):
    """ Ensures that the VM/instance is suspended for the test

    Uses calls to the actual provider api; it will suspend the vm if necessary.

    Args:
        provider.mgmt: Provider class object
        vm_name: Name of the VM/instance
    """
    return provider.mgmt.get_vm(vm_name).ensure_state(VmState.SUSPENDED)


@pytest.fixture(scope="function")
def ensure_vm_paused(provider, vm_name):
    """ Ensures that the VM/instance is paused for the test

    Uses calls to the actual provider api; it will pause the vm if necessary.

    Args:
        provider.mgmt: Provider class object
        vm_name: Name of the VM/instance
    """
    return provider.mgmt.get_vm(vm_name).ensure_state(VmState.PAUSED)
