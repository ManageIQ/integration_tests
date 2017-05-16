# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.vm import VM
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.services import requests
from cfme.web_ui import flash
from cfme import test_requirements

from utils.wait import wait_for
from utils import testgen

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    test_requirements.vm_migrate,
]


@pytest.fixture(scope="module")
def vm_name():
    return "test_migrate_" + fauxfactory.gen_alphanumeric()


@pytest.fixture(scope="module")
def test_vm(setup_provider_modscope, provider, vm_name, request):
    """Fixture to provision appliance to the provider being tested if necessary"""
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
@pytest.mark.meta(blockers=[1256903])
def test_vm_migrate(setup_provider, test_vm, provider):
    """Tests migration of a vm

    Metadata:
        test_flag: migrate, provision
    """
    # auto_test_services should exist to test migrate VM
    test_vm.migrate_vm("email@xyz.com", "first", "last")
    flash.assert_no_errors()
    row_description = test_vm.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=600, delay=20)
    assert row.request_state.text == 'Migrated'
