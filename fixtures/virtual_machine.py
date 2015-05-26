""" Fixtures ensuring that a VM/instance is in the specified state for the test
"""


import pytest
from utils.log import logger
from utils.wait import wait_for


@pytest.fixture
def verify_vm_running(provider_mgmt, vm_name):
    """ Ensures that the VM/instance is in running state for the test

    Uses calls to the actual provider api; it will start the vm if necessary.

    Args:
        provider_mgmt: :py:class:`utils.mgmt_system.MgmtSystemAPIBase` object
        vm_name: Name of the VM/instance
    """

    def _wait_for_vm_running():
        if provider_mgmt.is_vm_running(vm_name):
            return True
        elif provider_mgmt.is_vm_stopped(vm_name) or \
                provider_mgmt.can_suspend and provider_mgmt.is_vm_suspended(vm_name) or \
                provider_mgmt.can_pause and provider_mgmt.is_vm_paused(vm_name):
            provider_mgmt.start_vm(vm_name)

        logger.debug("Sleeping 15secs...(current state: {}, needed state: running)".format(
            provider_mgmt.vm_status(vm_name)
        ))
        return False

    return wait_for(_wait_for_vm_running, num_sec=360, delay=15)


@pytest.fixture
def verify_vm_stopped(provider_mgmt, vm_name):
    """ Ensures that the VM/instance is stopped for the test

    Uses calls to the actual provider api; it will stop the vm if necessary.

    Args:
        provider_mgmt: :py:class:`utils.mgmt_system.MgmtSystemAPIBase` object
        vm_name: Name of the VM/instance
    """

    def _wait_for_vm_stopped():
        if provider_mgmt.is_vm_stopped(vm_name):
            return True
        elif provider_mgmt.is_vm_running(vm_name):
            provider_mgmt.stop_vm(vm_name)
        elif provider_mgmt.can_suspend and provider_mgmt.is_vm_suspended(vm_name) or \
                provider_mgmt.can_pause and provider_mgmt.is_vm_paused(vm_name):
            provider_mgmt.start_vm(vm_name)

        logger.debug("Sleeping 15secs...(current state: {}, needed state: stopped)".format(
            provider_mgmt.vm_status(vm_name)
        ))
        return False

    return wait_for(_wait_for_vm_stopped, num_sec=360, delay=15)


@pytest.fixture
def verify_vm_suspended(provider_mgmt, vm_name):
    """ Ensures that the VM/instance is suspended for the test

    Uses calls to the actual provider api; it will suspend the vm if necessary.

    Args:
        provider_mgmt: :py:class:`utils.mgmt_system.MgmtSystemAPIBase` object
        vm_name: Name of the VM/instance
    """

    def _wait_for_vm_suspended():
        if provider_mgmt.is_vm_suspended(vm_name):
            return True
        elif provider_mgmt.is_vm_running(vm_name):
            provider_mgmt.suspend_vm(vm_name)
        elif provider_mgmt.is_vm_stopped(vm_name) or \
                provider_mgmt.can_pause and provider_mgmt.is_vm_paused(vm_name):
            provider_mgmt.start_vm(vm_name)

        logger.debug("Sleeping 15secs...(current state: {}, needed state: suspended)".format(
            provider_mgmt.vm_status(vm_name)
        ))
        return False

    return wait_for(_wait_for_vm_suspended, num_sec=360, delay=15)


@pytest.fixture
def verify_vm_paused(provider_mgmt, vm_name):
    """ Ensures that the VM/instance is paused for the test

    Uses calls to the actual provider api; it will pause the vm if necessary.

    Args:
        provider_mgmt: :py:class:`utils.mgmt_system.MgmtSystemAPIBase` object
        vm_name: Name of the VM/instance
    """

    def _wait_for_vm_paused():
        if provider_mgmt.is_vm_paused(vm_name):
            return True
        elif provider_mgmt.is_vm_running(vm_name):
            provider_mgmt.pause_vm(vm_name)
        elif provider_mgmt.is_vm_stopped(vm_name) or \
                provider_mgmt.can_suspend and provider_mgmt.is_vm_suspended(vm_name):
            provider_mgmt.start_vm(vm_name)

        logger.debug("Sleeping 15secs...(current state: {}, needed state: paused)".format(
            provider_mgmt.vm_status(vm_name)
        ))
        return False

    return wait_for(_wait_for_vm_paused, num_sec=360, delay=15)
