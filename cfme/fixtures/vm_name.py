# -*- coding: utf-8 -*-
import pytest
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger


# TODO This fixture needs to go way, cleanup shouldn't happen here and should happen in the
# otherlocations
@pytest.yield_fixture(scope='function')
def vm_name(provider):
    # also tries to delete the VM that gets made with this name
    vm_name = random_vm_name('scat')
    yield vm_name
    try:
        logger.info('Cleaning up VM %s on provider %s', vm_name, provider.key)
        provider.mgmt.delete_vm(vm_name)
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s', vm_name, provider.key)
