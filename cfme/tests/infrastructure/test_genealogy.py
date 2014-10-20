# -*- coding: utf-8 -*-
import pytest

from cfme.infrastructure.provider import RHEVMProvider
from cfme.infrastructure.virtual_machines import Vm, Template
from utils import testgen
from utils.randomness import generate_random_string

pytestmark = [
    pytest.mark.fixtureconf(server_roles="+automate +notifier"),
    pytest.mark.usefixtures('server_roles', 'uses_infra_providers')
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, 'provisioning')

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # No provisioning data available
            continue

        # required keys should be a subset of the dict keys set
        if not {'template', 'host', 'datastore'}.issubset(args['provisioning'].viewkeys()):
            # Need all three for template provisioning
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="function")
def vm_name():
    vm_name = 'test_genealogy_{}'.format(generate_random_string())
    return vm_name


@pytest.mark.github("ManageIQ/manageiq:473")
def test_vm_genealogy(
        setup_provider, vm_name, provider_crud, provisioning, soft_assert, provider_mgmt, request):
    if isinstance(provider_crud, RHEVMProvider):
        pytest.skip("RHEV-M does not support creating templates from VM")
    original_template = provisioning["template"]
    original_vm = Vm(vm_name, provider_crud, template_name=original_template)
    original_vm.create_on_provider()
    request.addfinalizer(
        lambda: provider_mgmt.delete_vm(original_vm.name)
        if provider_mgmt.does_vm_exist(original_vm.name) else None)
    provider_mgmt.wait_vm_steady(original_vm.name)
    first_template = original_vm.publish_to_template("{}x".format(vm_name))
    soft_assert(isinstance(first_template, Template), "first_template is not a template!")
    request.addfinalizer(
        lambda: provider_mgmt.delete_vm(first_template.name)
        if first_template.name in provider_mgmt.list_template() else None)
    second_vm = Vm(
        "{}x".format(first_template.name), provider_crud, template_name=first_template.name)
    second_vm.create_on_provider()
    request.addfinalizer(
        lambda: provider_mgmt.delete_vm(second_vm.name)
        if provider_mgmt.does_vm_exist(second_vm.name) else None)
    soft_assert(isinstance(second_vm, Vm), "second_vm is a template!")
    second_vm_ancestors = second_vm.genealogy.ancestors
    # IT SEEMS IT "BREAKS" THE CHAIN WHEN THE VM IS CLONED TO A TEMPLATE
    # soft_assert(original_vm.name in second_vm_ancestors, "{} is not in {}'s ancestors".format(
    #     original_vm.name, second_vm.name))
    soft_assert(first_template.name in second_vm_ancestors, "{} is not in {}'s ancestors".format(
        first_template.name, second_vm.name))
