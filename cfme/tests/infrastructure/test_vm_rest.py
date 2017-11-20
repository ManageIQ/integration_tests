# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import vm as _vm
from cfme.utils import error
from cfme.utils.rest import assert_response, delete_resources_from_collection
from cfme.utils.wait import wait_for


pytestmark = [test_requirements.provision]


@pytest.fixture(scope="function")
def a_provider(request):
    return _a_provider(request)


@pytest.fixture(scope="function")
def vm_name(request, a_provider, appliance):
    return _vm(request, a_provider, appliance.rest_api)


@pytest.mark.parametrize(
    'from_detail', [True, False],
    ids=['from_detail', 'from_collection'])
def test_edit_vm(request, vm_name, appliance, from_detail):
    """Tests edit VMs using REST API.

    Testing BZ 1428250.

    Metadata:
        test_flag: rest
    """
    vm = appliance.rest_api.collections.vms.get(name=vm_name)
    request.addfinalizer(vm.action.delete)
    new_description = 'Test REST VM {}'.format(fauxfactory.gen_alphanumeric(5))
    payload = {'description': new_description}
    if from_detail:
        edited = vm.action.edit(**payload)
        assert_response(appliance)
    else:
        payload.update(vm._ref_repr())
        edited = appliance.rest_api.collections.vms.action.edit(payload)
        assert_response(appliance)
        edited = edited[0]

    record, __ = wait_for(
        lambda: appliance.rest_api.collections.vms.find_by(
            description=new_description) or False,
        num_sec=100,
        delay=5,
    )
    vm.reload()
    assert vm.description == edited.description == record[0].description


@pytest.mark.tier(3)
@pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
def test_delete_vm_from_detail(vm_name, appliance, method):
    vm = appliance.rest_api.collections.vms.get(name=vm_name)
    del_action = getattr(vm.action.delete, method.upper())
    del_action()
    assert_response(appliance)
    wait_for(
        lambda: not appliance.rest_api.collections.vms.find_by(name=vm_name), num_sec=300, delay=10)
    with error.expected('ActiveRecord::RecordNotFound'):
        del_action()
    assert_response(appliance, http_status=404)


@pytest.mark.tier(3)
def test_delete_vm_from_collection(vm_name, appliance):
    vm = appliance.rest_api.collections.vms.get(name=vm_name)
    collection = appliance.rest_api.collections.vms
    delete_resources_from_collection(collection, [vm], not_found=True, num_sec=300, delay=10)
