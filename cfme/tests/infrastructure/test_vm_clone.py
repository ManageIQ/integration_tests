# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.provider import cleanup_vm
from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import testgen
from cfme.utils.log import logger

pytestmark = [
    pytest.mark.meta(roles="+automate")
]


pytest_generate_tests = testgen.generate([VMwareProvider], required_fields=[
    ['provisioning', 'template'],
    ['provisioning', 'host'],
    ['provisioning', 'datastore']
], scope="module")


@pytest.fixture(scope="function")
def clone_vm_name():
    clone_vm_name = 'test_cloning_{}'.format(fauxfactory.gen_alphanumeric())
    return clone_vm_name


@pytest.fixture
def create_vm(appliance, provider, setup_provider, request):
    """Fixture to provision vm to the provider being tested"""
    vm_name = 'test_clone_{}'.format(fauxfactory.gen_alphanumeric())
    vm = VM.factory(vm_name, provider)
    logger.info("provider_key: %s", provider.key)

    @request.addfinalizer
    def _cleanup():
        vm.delete_from_provider()

    if not provider.mgmt.does_vm_exist(vm.name):
        logger.info("deploying %s on provider %s", vm.name, provider.key)
        vm.create_on_provider(allow_skip="default", find_in_cfme=False)
    return vm


@pytest.mark.usefixtures("setup_provider")
@pytest.mark.long_running
def test_vm_clone(appliance, provider, clone_vm_name, request, create_vm):
    request.addfinalizer(lambda: cleanup_vm(clone_vm_name, provider))
    provision_type = 'VMware'
    create_vm.clone_vm("email@xyz.com", "first", "last", clone_vm_name, provision_type)
    request_description = clone_vm_name
    request_row = appliance.collections.requests.instantiate(request_description,
                                                             partial_check=True)
    request_row.wait_for_request(method='ui')
    assert request_row.is_succeeded(method='ui')
