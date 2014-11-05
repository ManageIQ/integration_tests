""" Fixtures ensuring that a VM/instance is in the specified state for the test
"""


import pytest
import re
from utils.log import logger
from utils.wait import wait_for

ON_REGEX = re.compile(r'up|POWERED\ ON|running|ACTIVE|poweredOn')
OFF_REGEX = re.compile(r'down|POWERED\ OFF|stopped|poweredOff')
SUSPEND_REGEX = re.compile(r'SUSPENDED|suspended')


@pytest.fixture
def verify_vm_running(provider_mgmt, vm_name):
    """ Ensures that the VM/instance is in running state for the test

    Uses calls to the actual provider api; it will start the vm if necessary.

    Args:
        provider_mgmt: :py:class:`utils.mgmt_system.MgmtSystemAPIBase` object
        vm_name: Name of the VM/instance
    """

    def _wait_for_vm_running():
        state = provider_mgmt.vm_status(vm_name)
        if ON_REGEX.match(state):
            return True
        elif OFF_REGEX.match(state) or SUSPEND_REGEX.match(state):
            provider_mgmt.start_vm(vm_name)
        logger.debug("Sleeping 15secs...(current state: " + state + ", needed state: running)")
        return False

    return wait_for(_wait_for_vm_running, num_sec=300, delay=15)


@pytest.fixture
def verify_vm_stopped(provider_mgmt, vm_name):
    """ Ensures that the VM/instance is stopped for the test

    Uses calls to the actual provider api; it will stop the vm if necessary.

    Args:
        provider_mgmt: :py:class:`utils.mgmt_system.MgmtSystemAPIBase` object
        vm_name: Name of the VM/instance
    """

    def _wait_for_vm_stopped():
        state = provider_mgmt.vm_status(vm_name)
        if OFF_REGEX.match(state):
            return True
        elif ON_REGEX.match(state):
            provider_mgmt.stop_vm(vm_name)
        elif SUSPEND_REGEX.match(state):
            provider_mgmt.start_vm(vm_name)
        logger.debug("Sleeping 15secs...(current state: " + state + ", needed state: stopped)")
        return False

    return wait_for(_wait_for_vm_stopped, num_sec=300, delay=15)


@pytest.fixture
def verify_vm_suspended(provider_mgmt, vm_name):
    """ Ensures that the VM/instance is suspended for the test

    Uses calls to the actual provider api; it will suspend the vm if necessary.

    Args:
        provider_mgmt: :py:class:`utils.mgmt_system.MgmtSystemAPIBase` object
        vm_name: Name of the VM/instance
    """

    def _wait_for_vm_suspended():
        state = provider_mgmt.vm_status(vm_name)
        if SUSPEND_REGEX.match(state):
            return
        elif ON_REGEX.match(state):
            provider_mgmt.suspend_vm(vm_name)
        elif OFF_REGEX.match(state):
            provider_mgmt.start_vm(vm_name)
        logger.debug("Sleeping 15secs...(current state: " + state + ", needed state: suspended)")
        return False

    return wait_for(_wait_for_vm_suspended, num_sec=300, delay=15)
