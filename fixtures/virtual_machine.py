import pytest
import re
from utils.log import logger
from utils.wait import wait_for

ON_REGEX = re.compile(r'up|POWERED\ ON|running')
DOWN_REGEX = re.compile(r'down|POWERED\ OFF|stopped')
SUSPEND_REGEX = re.compile(r'SUSPENDED|suspended')


@pytest.fixture
def verify_vm_running(provider_mgmt, vm_name):
    '''
        Verifies the vm is in the running state for the test.Uses calls to the actual provider api.
          It will start the vm if necessary.

        :param provider: provider_mgmt object
        :type  provider: object
        :param vm_name: name of the vm
        :type  vm_name: str
        :return: None
        :rtype: None
    '''

    def _wait_for_vm_running():
        state = provider_mgmt.vm_status(vm_name)
        if ON_REGEX.match(state):
            return True
        elif DOWN_REGEX.match(state) or SUSPEND_REGEX.match(state):
            provider_mgmt.start_vm(vm_name)
        logger.debug("Sleeping 15secs...(current state: " + state + ", needed state: running)")

    return wait_for(_wait_for_vm_running, num_sec=300, delay=15)


@pytest.fixture
def verify_vm_stopped(provider_mgmt, vm_name):
    '''
        Verifies the vm is in the stopped state for the test.Uses calls to the actual provider api.
          It will stop the vm if necessary.

        :param provider: provider_mgmt object
        :type  provider: object
        :param vm_name: name of the vm
        :type  vm_name: str
        :return: None
        :rtype: None
    '''

    def _wait_for_vm_stopped():
        state = provider_mgmt.vm_status(vm_name)
        if DOWN_REGEX.match(state):
            return True
        elif ON_REGEX.match(state):
            provider_mgmt.stop_vm(vm_name)
        elif SUSPEND_REGEX.match(state):
            provider_mgmt.start_vm(vm_name)
        logger.debug("Sleeping 15secs...(current state: " + state + ", needed state: stopped)")

    return wait_for(_wait_for_vm_stopped, num_sec=300, delay=15)


@pytest.fixture
def verify_vm_suspended(provider_mgmt, vm_name):
    '''
        Verifies the vm is in the suspended state for the test.Uses calls to the actual provider
        api.It will start and suspend the vm if necessary.

        :param provider: provider_mgmt object
        :type  provider: object
        :param vm_name: name of the vm
        :type  vm_name: str
        :return: None
        :rtype: None
    '''

    def _wait_for_vm_suspended():
        state = provider_mgmt.vm_status(vm_name)
        if SUSPEND_REGEX.match(state):
            return
        elif ON_REGEX.match(state):
            provider_mgmt.suspend_vm(vm_name)
        elif ON_REGEX.match(state):
            provider_mgmt.start_vm(vm_name)
        logger.debug("Sleeping 15secs...(current state: " + state + ", needed state: suspended)")

    return wait_for(_wait_for_vm_suspended, num_sec=300, delay=15)
