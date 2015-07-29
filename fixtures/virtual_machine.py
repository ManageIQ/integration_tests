""" Fixtures ensuring that a VM/instance is in the specified state for the test
"""


import pytest
from utils.log import logger
from utils.wait import wait_for


@pytest.fixture
def verify_vm_running(provider, vm_name):
    """ Ensures that the VM/instance is in running state for the test

    Uses calls to the actual provider api; it will start the vm if necessary.

    Args:
        provider: Provider class object
        vm_name: Name of the VM/instance
    """

    def _wait_for_vm_running():
        if provider.mgmt.is_vm_running(vm_name):
            return True
        elif provider.mgmt.is_vm_stopped(vm_name) or \
                provider.mgmt.can_suspend and provider.mgmt.is_vm_suspended(vm_name) or \
                provider.mgmt.can_pause and provider.mgmt.is_vm_paused(vm_name):
            provider.mgmt.start_vm(vm_name)

        logger.debug("Sleeping 15secs...(current state: {}, needed state: running)".format(
            provider.mgmt.vm_status(vm_name)
        ))
        return False

    return wait_for(_wait_for_vm_running, num_sec=360, delay=15)


@pytest.fixture
def verify_vm_stopped(provider, vm_name):
    """ Ensures that the VM/instance is stopped for the test

    Uses calls to the actual provider api; it will stop the vm if necessary.

    Args:
        provider: Provider class object
        vm_name: Name of the VM/instance
    """

    def _wait_for_vm_stopped():
        if provider.mgmt.is_vm_stopped(vm_name):
            return True
        elif provider.mgmt.is_vm_running(vm_name):
            provider.mgmt.stop_vm(vm_name)
        elif provider.mgmt.can_suspend and provider.mgmt.is_vm_suspended(vm_name) or \
                provider.mgmt.can_pause and provider.mgmt.is_vm_paused(vm_name):
            provider.mgmt.start_vm(vm_name)

        logger.debug("Sleeping 15secs...(current state: {}, needed state: stopped)".format(
            provider.mgmt.vm_status(vm_name)
        ))
        return False

    return wait_for(_wait_for_vm_stopped, num_sec=360, delay=15)


@pytest.fixture
def verify_vm_suspended(provider, vm_name):
    """ Ensures that the VM/instance is suspended for the test

    Uses calls to the actual provider api; it will suspend the vm if necessary.

    Args:
        provider.mgmt: Provider class object
        vm_name: Name of the VM/instance
    """

    def _wait_for_vm_suspended():
        if provider.mgmt.is_vm_suspended(vm_name):
            return True
        elif provider.mgmt.is_vm_running(vm_name):
            provider.mgmt.suspend_vm(vm_name)
        elif provider.mgmt.is_vm_stopped(vm_name) or \
                provider.mgmt.can_pause and provider.mgmt.is_vm_paused(vm_name):
            provider.mgmt.start_vm(vm_name)

        logger.debug("Sleeping 15secs...(current state: {}, needed state: suspended)".format(
            provider.mgmt.vm_status(vm_name)
        ))
        return False

    return wait_for(_wait_for_vm_suspended, num_sec=360, delay=15)


@pytest.fixture
def verify_vm_paused(provider, vm_name):
    """ Ensures that the VM/instance is paused for the test

    Uses calls to the actual provider api; it will pause the vm if necessary.

    Args:
        provider.mgmt: Provider class object
        vm_name: Name of the VM/instance
    """

    def _wait_for_vm_paused():
        if provider.mgmt.is_vm_paused(vm_name):
            return True
        elif provider.mgmt.is_vm_running(vm_name):
            provider.mgmt.pause_vm(vm_name)
        elif provider.mgmt.is_vm_stopped(vm_name) or \
                provider.mgmt.can_suspend and provider.mgmt.is_vm_suspended(vm_name):
            provider.mgmt.start_vm(vm_name)

        logger.debug("Sleeping 15secs...(current state: {}, needed state: paused)".format(
            provider.mgmt.vm_status(vm_name)
        ))
        return False

    return wait_for(_wait_for_vm_paused, num_sec=360, delay=15)
