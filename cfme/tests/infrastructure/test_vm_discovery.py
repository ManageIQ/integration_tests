import pytest
from cfme.infrastructure import virtual_machines
from utils import testgen
from utils.providers import setup_provider
from utils.randomness import generate_random_string
from utils.wait import wait_for, TimedOutError


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture
def provider_init(provider_key):
    """cfme/infrastructure/provider.py provider object."""
    try:
        setup_provider(provider_key)
    except Exception as e:
        pytest.skip("It's not possible to set up this provider, therefore skipping. Exception: "
            + str(e))


@pytest.fixture(scope="class")
def vm_name():
    return "test_dscvry_" + generate_random_string()


def test_vm_discovery(request, provider_crud, provider_init, provider_mgmt, vm_name):
    """
    Tests whether cfme will discover a vm change
    (add/delete) without being manually refreshed.
    """
    vm = virtual_machines.Vm(vm_name, provider_crud)
    request.addfinalizer(vm.delete_from_provider)
    if not provider_mgmt.does_vm_exist(vm_name):
        vm.create_on_provider()
    try:
        vm.wait_for_vm_to_appear(timeout=600, load_details=False)
    except TimedOutError:
        return False
    vm.delete_from_provider()
    virtual_machines.load_archived_vms()
    try:
        wait_for(lambda: vm.find_quadicon(True, False, False),
                num_secs=800, delay=30, handle_exception=True)
    except TimedOutError:
        return False
