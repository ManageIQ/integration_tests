# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from cfme.cloud import instance
from utils import testgen
from utils.virtual_machines import deploy_template
from utils.providers import setup_provider
from utils.wait import wait_for, TimedOutError

pytest_generate_tests = testgen.generate(testgen.cloud_providers, scope="module")


@pytest.fixture
def provider_init(provider_key):
    """cfme/cloud/provider.py provider object."""
    setup_provider(provider_key)


@pytest.fixture(scope="class")
def instance_name():
    return "test_dscvry_" + fauxfactory.gen_alphanumeric()


def _check_instance(test_instance):
    if not isinstance(test_instance, instance.Instance):
        raise Exception("test_instance must be an instance of cfme.cloud.instance.Instance")


def _does_instance_exist_in_CFME(test_instance):
    _check_instance(test_instance)
    pytest.sel.force_navigate('clouds_instances_by_provider',
        context={'provider_name': test_instance.provider_crud})
    pytest.sel.click(test_instance.find_quadicon(True, False, False))
    return True


def _is_instance_archived(test_instance):
    _check_instance(test_instance)
    pytest.sel.force_navigate('clouds_instances_archived_branch')
    pytest.sel.click(test_instance.find_quadicon(True, False, False))
    return True


def test_cloud_instance_discovery(request, provider_crud, provider_init, provider_mgmt,
        instance_name):
    """
    Tests whether cfme will successfully discover a cloud instance change
    (add/delete).
    As there is currently no way to listen to AWS events,
    CFME must be refreshed manually to see the changes.

    Metadata:
        test_flag: discovery
    """
    if not provider_mgmt.does_vm_exist(instance_name):
        deploy_template(provider_crud.key, instance_name, allow_skip="default")
    test_instance = instance.instance_factory(instance_name, provider_crud)
    request.addfinalizer(test_instance.delete_from_provider)
    try:
        wait_for(_does_instance_exist_in_CFME, [test_instance], num_sec=800, delay=30,
            fail_func=test_instance.provider_crud.refresh_provider_relationships,
            handle_exception=True)
    except TimedOutError:
        pytest.fail("Instance was not found in CFME")
    test_instance.delete_from_provider()
    try:
        wait_for(_is_instance_archived, [test_instance], num_sec=800, delay=30,
            fail_func=test_instance.provider_crud.refresh_provider_relationships,
            handle_exception=True)
    except TimedOutError:
        pytest.fail("instance was not found in Archives")
