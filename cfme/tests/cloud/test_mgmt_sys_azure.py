import pytest

import cfme.web_ui.flash as flash
import utils.error as error
from cfme import Credential
from utils import testgen, version
from utils.update import update
from utils.mgmt_system import azuresms


def test_azure_vm_list():
    """ This is a POC test to authenticate the Azure Management System Module."""
    az = azuresms.AZURESystem()
    az.list_vm('WS2012')

def test_azure_vm_state():
    """ This is a POC test to get the VM State from Azure instance."""
    test_vm_name = 'ecazure2'
    expected_state = 'Stopped'
    az = azuresms.AZURESystem()
    test_vm_state = az.vm_status(test_vm_name)
    assert expected_state == test_vm_state

def test_azure_vm_start():
    """ This is a POC test to start an existing VM from Azure instance."""
    test_vm_name = 'ecazure2'
    az = azuresms.AZURESystem()
    test_vm_state = az.start_vm(test_vm_name)

def test_azure_vm_stop():
    """ This is a POC test to stop an existing VM from Azure instance."""
    test_vm_name = 'ecazure2'
    az = azuresms.AZURESystem()
    test_vm_state = az.stop_vm(test_vm_name, 'StoppedDeallocated')
