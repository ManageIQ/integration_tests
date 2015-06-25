# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import time
from cfme.cloud.instance import EC2Instance, OpenStackInstance
from cfme.exceptions import CFMEException
from cfme.infrastructure.virtual_machines import Vm
from cfme.infrastructure.provider import SCVMMProvider
from utils import testgen
from utils.log import logger
from utils.wait import TimedOutError


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.all_providers(metafunc)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture(scope="module")
def vm_name():
    return "test_dscvry_" + fauxfactory.gen_alpha(8).lower()


@pytest.fixture(scope="module")
def vm_crud(vm_name, provider_crud, provider_type):
    cls = Vm
    if provider_type == "ec2":
        cls = EC2Instance
    elif provider_type == "openstack":
        cls = OpenStackInstance
    return cls(vm_name, provider_crud)


def if_scvmm_refresh_provider(provider):
    # No eventing from SCVMM so force a relationship refresh
    if isinstance(provider, SCVMMProvider):
        provider.refresh_provider_relationships()


def wait_for_vm_state_changes(vm, timeout=600):

    count = 0
    while count < timeout:
        try:
            quadicon = vm.find_quadicon(refresh=True, from_any_provider=True)
            logger.info("Quadicon state for {} is {}".format(vm.name, repr(quadicon.state)))
            if "archived" in quadicon.state.lower():
                return True
            elif "orphaned" in quadicon.state.lower():
                raise CFMEException("VM should be Archived but it is Orphaned now.")
        except Exception as e:
            logger.exception(e)
            pass
        time.sleep(15)
        count += 15
    if count > timeout:
        raise CFMEException("VM should be Archived but it is Orphaned now.")


def test_vm_discovery(request, setup_provider, provider_crud, provider_mgmt, vm_crud):
    """
    Tests whether cfme will discover a vm change
    (add/delete) without being manually refreshed.

    Metadata:
        test_flag: discovery
    """

    @request.addfinalizer
    def _cleanup():
        vm_crud.delete_from_provider()
        if_scvmm_refresh_provider(provider_crud)

    vm_crud.create_on_provider(allow_skip="default")
    if_scvmm_refresh_provider(provider_crud)

    try:
        vm_crud.wait_to_appear(timeout=600, load_details=False)
    except TimedOutError:
        pytest.fail("VM was not found in CFME")
    vm_crud.delete_from_provider()
    if_scvmm_refresh_provider(provider_crud)
    wait_for_vm_state_changes(vm_crud)
