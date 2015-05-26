# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.infrastructure.virtual_machines import Vm
from utils import testgen


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['scvmm'], 'small_template')
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')


@pytest.mark.meta(blockers=[1178961])
@pytest.mark.uncollectif(
    lambda provider_data: "host_group" in provider_data.get("provisioning", {}))
def test_no_dvd_ruins_refresh(provider_mgmt, provider_crud, provider_data, small_template):
    host_group = provider_data["provisioning"]["host_group"]
    with provider_mgmt.with_vm(
            small_template, vm_name="test_no_dvd_{}".format(fauxfactory.gen_alpha()),
            host_group=host_group) as vm_name:
        provider_mgmt.disconnect_dvd_drives(vm_name)
        vm = Vm(vm_name, provider_crud)
        provider_crud.refresh_provider_relationships()
        vm.wait_to_appear()
