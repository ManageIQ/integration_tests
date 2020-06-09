import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.providers import ProviderFilter
from cfme.utils.wait import wait_for


pytestmark = [
    test_requirements.rest,
    pytest.mark.usefixtures('uses_infra_providers', 'uses_cloud_providers'),
    pytest.mark.tier(2),
    pytest.mark.provider([CloudProvider, InfraProvider], scope='module'),
    pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"]),
]


@pytest.fixture(scope='function')
def vm_name(create_vm):
    return create_vm.name


def wait_for_vm_state_change(create_vm, state):
    if create_vm.provider.one_of(GCEProvider, EC2Provider, SCVMMProvider):
        num_sec = 4000  # extra time for slow providers
    else:
        num_sec = 1200
    create_vm.wait_for_power_state_change_rest(desired_state=state, timeout=num_sec)


def verify_vm_power_state(vm, state):
    vm.reload()
    return vm.power_state == state


def verify_action_result(rest_api, assert_success=True):
    assert rest_api.response.status_code == 200
    response = rest_api.response.json()
    if 'results' in response:
        response = response['results'][0]
    message = response['message']
    success = response['success']
    if assert_success:
        assert success
    return success, message


@pytest.mark.parametrize('create_vm', ['small_template'], indirect=True)
def test_stop_vm_rest(appliance, create_vm, ensure_vm_running, soft_assert, from_detail):
    """Test stop of vm

    Prerequisities:

        * An appliance with ``/api`` available.
        * VM

    Steps:

        * POST /api/vms/<id> (method ``stop``)
        OR
        * POST /api/vms (method ``stop``) with ``href`` of the vm or vms

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/4h
    """
    rest_api = appliance.rest_api
    create_vm.wait_for_vm_state_change(desired_state=create_vm.STATE_ON)
    vm = rest_api.collections.vms.get(name=create_vm.name)

    if from_detail:
        vm.action.stop()
    else:
        rest_api.collections.vms.action.stop(vm)
    verify_action_result(rest_api)
    wait_for_vm_state_change(create_vm, create_vm.STATE_OFF)
    soft_assert(not verify_vm_power_state(vm, create_vm.STATE_ON), "vm still running")


@pytest.mark.parametrize('create_vm', ['small_template'], indirect=True)
def test_start_vm_rest(appliance, create_vm, ensure_vm_stopped, soft_assert, from_detail):
    """Test start vm

    Prerequisities:

        * An appliance with ``/api`` available.
        * VM

    Steps:

        * POST /api/vms/<id> (method ``start``)
        OR
        * POST /api/vms (method ``start``) with ``href`` of the vm or vms

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/4h
    """
    rest_api = appliance.rest_api
    create_vm.wait_for_vm_state_change(desired_state=create_vm.STATE_OFF, timeout=1200)
    vm = rest_api.collections.vms.get(name=create_vm.name)

    if from_detail:
        vm.action.start()
    else:
        rest_api.collections.vms.action.start(vm)
    verify_action_result(rest_api)
    wait_for_vm_state_change(create_vm, create_vm.STATE_ON)
    soft_assert(verify_vm_power_state(vm, create_vm.STATE_ON), "vm not running")


@pytest.mark.parametrize('create_vm', ['small_template'], indirect=True)
def test_suspend_vm_rest(appliance, create_vm, ensure_vm_running, soft_assert, from_detail):
    """Test suspend vm

    Prerequisities:

        * An appliance with ``/api`` available.
        * VM

    Steps:

        * POST /api/vms/<id> (method ``suspend``)
        OR
        * POST /api/vms (method ``suspend``) with ``href`` of the vm or vms

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/4h
    """
    rest_api = appliance.rest_api
    create_vm.wait_for_vm_state_change(desired_state=create_vm.STATE_ON)
    vm = rest_api.collections.vms.get(name=create_vm.name)

    if from_detail:
        vm.action.suspend()
    else:
        rest_api.collections.vms.action.suspend(vm)
    success, message = verify_action_result(rest_api, assert_success=False)
    if create_vm.provider.one_of(GCEProvider, EC2Provider):
        assert success is False
        assert "not available" in message
    else:
        assert success
        wait_for_vm_state_change(create_vm, create_vm.STATE_SUSPENDED)
        soft_assert(verify_vm_power_state(vm, create_vm.STATE_SUSPENDED), "vm not suspended")


@pytest.mark.provider(
    gen_func=providers,
    filters=[ProviderFilter(classes=[CloudProvider, InfraProvider]),
             ProviderFilter(classes=[RHEVMProvider, AzureProvider], inverted=True)],
)
@pytest.mark.parametrize('create_vm', ['small_template'], indirect=True)
def test_reset_vm_rest(create_vm, ensure_vm_running, from_detail, appliance, provider):
    """
    Test reset vm

    Prerequisities:

        * An appliance with ``/api`` available.
        * VM

    Steps:

        * POST /api/vms/<id> (method ``reset``)
        OR
        * POST /api/vms (method ``reset``) with ``href`` of the vm or vms

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/4h
    """
    rest_api = appliance.rest_api
    create_vm.wait_for_vm_state_change(desired_state=create_vm.STATE_ON)
    vm = rest_api.collections.vms.get(name=create_vm.name)

    old_date = vm.updated_on
    if from_detail:
        vm.action.reset()
    else:
        rest_api.collections.vms.action.reset(vm)
    success, message = verify_action_result(rest_api, assert_success=False)
    unsupported_providers = (GCEProvider, EC2Provider)
    if create_vm.provider.one_of(*unsupported_providers):
        assert success is False
        assert "not available" in message
    else:
        assert success
        wait_for(lambda: vm.updated_on >= old_date,
            num_sec=600, delay=20, fail_func=vm.reload, message='Wait for VM to reset')
