# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from utils.log import logger


@pytest.yield_fixture(scope='function')
def vm_name(provider):
    # also tries to delete the VM that gets made with this name
    vm_name = 'test_servicecatalog-{}'.format(fauxfactory.gen_alphanumeric())
    yield vm_name
    try:
        logger.info('Cleaning up VM %s on provider %s', vm_name, provider.key)
        provider.mgmt.delete_vm(vm_name)
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s', vm_name, provider.key)
