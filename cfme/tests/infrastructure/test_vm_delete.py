import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.utils.generators import random_vm_name
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.provider([RHEVMProvider], scope="module"),
    pytest.mark.usefixtures('setup_provider'),
    test_requirements.rhev
]


@pytest.fixture(scope="module")
def vm_test(provider):
    collection = provider.appliance.provider_based_collection(provider)
    vm_name = random_vm_name(context="del-test")
    vm = collection.instantiate(vm_name, provider)
    vm.create_on_provider(allow_skip="default", find_in_cfme=True)
    vm.wait_to_appear(timeout=900, load_details=False)
    yield vm

    if vm.exists:
        vm.cleanup_on_provider()


@pytest.mark.rhv2
@pytest.mark.meta(automates=[1592430])
def test_delete_vm_on_provider_side(vm_test, provider):
    """ Delete VM on the provider side and refresh relationships in CFME

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Infra

    Bugzilla:
        1592430
    """
    logs = LogValidator("/var/www/miq/vmdb/log/evm.log", failure_patterns=[".*ERROR.*"])
    logs.start_monitoring()
    vm_test.cleanup_on_provider()
    provider.refresh_provider_relationships()
    try:
        wait_for(provider.is_refreshed, func_kwargs={'refresh_delta': 10}, timeout=600)
    except TimedOutError:
        pytest.fail("Provider failed to refresh after VM was removed from the provider")
    assert logs.validate(wait="60s")
