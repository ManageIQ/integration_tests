# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.infrastructure.virtual_machines import Vm
from utils import testgen


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['scvmm'], 'small_template')
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope='module')


@pytest.mark.meta(blockers=[1178961])
@pytest.mark.uncollectif(
    lambda provider: "host_group" in provider.data.get("provisioning", {}),
    reason="No host group")
def test_no_dvd_ruins_refresh(provider, small_template):
    host_group = provider.data["provisioning"]["host_group"]
    with provider.mgmt.with_vm(
            small_template, vm_name="test_no_dvd_{}".format(fauxfactory.gen_alpha()),
            host_group=host_group) as vm_name:
        provider.mgmt.disconnect_dvd_drives(vm_name)
        vm = Vm(vm_name, provider)
        provider.refresh_provider_relationships()
        vm.wait_to_appear()
