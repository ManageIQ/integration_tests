# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import vm as _vm
from utils import error
from utils.wait import wait_for


pytestmark = [test_requirements.provision]


@pytest.fixture(scope="function")
def a_provider(request):
    return _a_provider(request)


@pytest.fixture(scope="function")
def vm_name(request, a_provider, appliance):
    return _vm(request, a_provider, appliance.rest_api)


@pytest.mark.tier(3)
@pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
def test_delete_vm_from_detail(vm_name, appliance, method):
    status = 204 if method == 'delete' else 200
    vm = appliance.rest_api.collections.vms.get(name=vm_name)
    vm.action.delete(force_method=method)
    assert appliance.rest_api.response.status_code == status
    wait_for(
        lambda: not appliance.rest_api.collections.vms.find_by(name=vm_name), num_sec=300, delay=10)
    with error.expected('ActiveRecord::RecordNotFound'):
        vm.action.delete(force_method=method)
    assert appliance.rest_api.response.status_code == 404


@pytest.mark.tier(3)
def test_delete_vm_from_collection(vm_name, appliance):
    vm = appliance.rest_api.collections.vms.get(name=vm_name)
    collection = appliance.rest_api.collections.vms
    collection.action.delete(vm)
    assert appliance.rest_api.response.status_code == 200
    wait_for(lambda: not collection.find_by(name=vm_name), num_sec=300, delay=10)
    with error.expected('ActiveRecord::RecordNotFound'):
        collection.action.delete(vm)
    assert appliance.rest_api.response.status_code == 404
