# -*- coding: utf-8 -*-
import pytest

from cfme.common.vm import VM
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme import test_requirements

from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils import testgen

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    test_requirements.vm_migrate,
]


@pytest.fixture(scope="module")
def new_vm(setup_provider_modscope, provider, request):
    """Fixture to provision appliance to the provider being tested if necessary"""
    vm_name = random_vm_name(context='migrate')
    vm = VM.factory(vm_name, provider, template_name=provider.data['small_template'])

    if not provider.mgmt.does_vm_exist(vm_name):
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
        request.addfinalizer(vm.delete_from_provider)
    return vm


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [VMwareProvider, RHEVMProvider])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[BZ(1478518, forced_streams=['5.7', '5.8', '5.9', 'upstream'])])
def test_vm_migrate(appliance, new_vm, provider):
    """Tests migration of a vm

    Metadata:
        test_flag: migrate, provision
    """
    # auto_test_services should exist to test migrate VM
    vm_host = new_vm.get_detail(properties=('Relationships', 'Host'))
    migrate_to = [vds.name for vds in provider.hosts if vds.name not in vm_host][0]
    new_vm.migrate_vm("email@xyz.com", "first", "last", host_name=migrate_to)
    request_description = new_vm.name
    cells = {'Description': request_description, 'Request Type': 'Migrate'}
    migrate_request = appliance.collections.requests.instantiate(request_description, cells=cells,
                                                                 partial_check=True)
    migrate_request.wait_for_request(method='ui')
    assert migrate_request.is_succeeded(method='ui')
