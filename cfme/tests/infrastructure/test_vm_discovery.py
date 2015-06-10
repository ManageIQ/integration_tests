# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import time
from cfme.exceptions import CFMEException
from cfme.infrastructure import virtual_machines
from cfme.infrastructure.provider import SCVMMProvider
from utils import testgen
from utils.wait import TimedOutError


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture(scope="class")
def vm_name():
    return "test_dscvry_" + fauxfactory.gen_alphanumeric(8)


def if_scvmm_refresh_provider(provider):
    # No eventing from SCVMM so force a relationship refresh
    if isinstance(provider, SCVMMProvider):
        provider.refresh_provider_relationships()


def wait_for_vm_state_changes(vm, timeout=600):

    count = 0
    while count < timeout:
        try:
            quadicon = vm.find_quadicon(refresh=True)
            if quadicon.state is 'Archived':
                return True
            elif quadicon.state is 'Orphaned':
                raise CFMEException("VM should be Archived but it is Orphaned now.")
        except:
            pass
        time.sleep(15)
        count += 15
    if count > timeout:
        raise CFMEException("VM should be Archived but it is Orphaned now.")


def test_vm_discovery(request, setup_provider, provider_crud, provider_mgmt, vm_name):
    """
    Tests whether cfme will discover a vm change
    (add/delete) without being manually refreshed.

    Metadata:
        test_flag: discovery
    """
    vm = virtual_machines.Vm(vm_name, provider_crud)

    def _cleanup():
        vm.delete_from_provider()
        if_scvmm_refresh_provider(provider_crud)

    request.addfinalizer(_cleanup)
    vm.create_on_provider(allow_skip="default")
    if_scvmm_refresh_provider(provider_crud)

    try:
        vm.wait_to_appear(timeout=600, load_details=False)
    except TimedOutError:
        pytest.fail("VM was not found in CFME")
    vm.delete_from_provider()
    if_scvmm_refresh_provider(provider_crud)
    wait_for_vm_state_changes(vm)
