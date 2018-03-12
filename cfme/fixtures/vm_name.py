# -*- coding: utf-8 -*-
import pytest

from cfme.common.vm import VM
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger


# TODO This fixture needs to go way, cleanup shouldn't happen here and should happen in the
# otherlocations
@pytest.yield_fixture(scope='function')
def vm_name(provider):
    # also tries to delete the VM that gets made with this name
    vm_name = random_vm_name('scat')
    yield vm_name
    scat_vm = "{}0001".format(vm_name)
    if scat_vm in provider.mgmt.list_vm():
        vm_name_to_cleanup = "{}0001".format(vm_name)
    else:
        vm_name_to_cleanup = vm_name
    VM.factory(vm_name_to_cleanup, provider).cleanup_on_provider()
