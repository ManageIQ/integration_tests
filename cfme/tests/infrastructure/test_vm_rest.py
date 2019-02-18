# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE
from cfme.rest.gen_data import vm as _vm
from cfme.utils.blockers import BZ
from cfme.utils.rest import assert_response
from cfme.utils.rest import delete_resources_from_collection
from cfme.utils.rest import delete_resources_from_detail
from cfme.utils.rest import query_resource_attributes
from cfme.utils.wait import wait_for
from cfme.utils.wait import wait_for_decorator

pytestmark = [
    test_requirements.provision,
    pytest.mark.provider(classes=[InfraProvider], selector=ONE),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture(scope='function')
def vm(request, provider, appliance):
    vm_name = _vm(request, provider, appliance)
    return appliance.rest_api.collections.vms.get(name=vm_name)


@pytest.mark.tier(3)
def test_query_vm_attributes(vm, soft_assert):
    """Tests access to VM attributes using /api/vms.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/4h
    """
    outcome = query_resource_attributes(vm)
    for failure in outcome.failed:
        if failure.type == 'attribute' and failure.name == 'policy_events' and BZ(
                1546995, forced_streams=['5.8', '5.9', 'upstream']).blocks:
            continue
        soft_assert(False, '{0} "{1}": status: {2}, error: `{3}`'.format(
            failure.type, failure.name, failure.response.status_code, failure.error))


@pytest.mark.tier(2)
@pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
def test_vm_scan(appliance, vm, from_detail):
    """Tests running VM scan using REST API.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/3h
    """
    if from_detail:
        response = vm.action.scan()
    else:
        response, = appliance.rest_api.collections.vms.action.scan(vm)
    assert_response(appliance)

    @wait_for_decorator(timeout='5m', delay=5, message='REST running VM scan finishes')
    def _finished():
        response.task.reload()
        if 'error' in response.task.status.lower():
            pytest.fail('Error when running scan vm method: `{}`'.format(response.task.message))
        return response.task.state.lower() == 'finished'


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    'from_detail', [True, False],
    ids=['from_detail', 'from_collection'])
def test_edit_vm(request, vm, appliance, from_detail):
    """Tests edit VMs using REST API.

    Testing BZ 1428250.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/4h
    """
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
def test_delete_vm_from_detail(vm, method):
    """
    Polarion:
        assignee: mkourim
        initialEstimate: 1/4h
    """
    delete_resources_from_detail([vm], method=method, num_sec=300, delay=10)


@pytest.mark.tier(3)
def test_delete_vm_from_collection(vm):
    """
    Polarion:
        assignee: mkourim
        initialEstimate: 1/4h
    """
    delete_resources_from_collection([vm], not_found=True, num_sec=300, delay=10)
