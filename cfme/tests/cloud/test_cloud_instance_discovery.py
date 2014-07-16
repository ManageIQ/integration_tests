import pytest
from cfme.cloud import instance
from utils import testgen
from utils.virtual_machines import deploy_template
from utils.providers import setup_provider
from utils.randomness import generate_random_string
from utils.wait import wait_for, TimedOutError


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.cloud_providers(metafunc)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture
def provider_init(provider_key):
    """cfme/cloud/provider.py provider object."""
    setup_provider(provider_key)


@pytest.fixture(scope="class")
def instance_name():
    return "test_dscvry_" + generate_random_string()


def _does_instance_exist_in_CFME(test_instance=None):
    if not isinstance(test_instance, instance.Instance):
        raise Exception("instance must be an instance of Instance")
    test_instance.provider_crud.refresh_provider_relationships()
    pytest.sel.force_navigate('clouds_instances_by_provider',
                              context={'provider_name': test_instance.provider_crud})
    pytest.sel.click(test_instance.find_quadicon(True, False, False))
    return True


def _is_instance_archived(test_instance=None):
    if not isinstance(test_instance, instance.Instance):
        raise Exception("instance must be an instance of Instance")
    test_instance.provider_crud.refresh_provider_relationships()
    pytest.sel.force_navigate('clouds_instances_archived_branch')
    pytest.sel.click(test_instance.find_quadicon(True, False, False))
    return True


def test_cloud_instance_discovery(request, provider_crud, provider_init,
                                  provider_mgmt, instance_name):
    """
    Tests whether cfme will successfully discover a cloud instance change
    (add/delete).
    As there is currently no way to listen to AWS events,
    CFME must be refreshed manually to see the changes.
    """
    if not provider_mgmt.does_vm_exist(instance_name):
        deploy_template(provider_crud.key, instance_name)
    test_instance = instance.instance_factory(instance_name, provider_crud)
    request.addfinalizer(test_instance.delete_from_provider)
    try:
        wait_for(lambda: _does_instance_exist_in_CFME(test_instance),
                 num_sec=800, delay=30, handle_exception=True)
    except TimedOutError:
        pytest.fail("Instance was not found in CFME")
    test_instance.delete_from_provider()
    try:
        wait_for(lambda: _is_instance_archived(test_instance),
                 num_sec=800, delay=30, handle_exception=True)
    except TimedOutError:
        pytest.fail("instance was not found in Archives")
