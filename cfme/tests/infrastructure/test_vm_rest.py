# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import vm as _vm
from utils.wait import wait_for


pytestmark = [test_requirements.provision]


@pytest.fixture(scope="function")
def a_provider():
    return _a_provider()


@pytest.fixture(scope="function")
def vm_name(request, a_provider, rest_api):
    return _vm(request, a_provider, rest_api)


@pytest.mark.tier(3)
@pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
def test_delete(vm_name, rest_api, from_detail):
    vm = rest_api.collections.vms.get(name=vm_name)
    assert "delete" in vm.action
    if from_detail:
        vm.action.delete()
    else:
        rest_api.collections.vms.action.delete(vm)
    wait_for(lambda: not rest_api.collections.vms.find_by(name=vm_name), num_sec=300, delay=10)
