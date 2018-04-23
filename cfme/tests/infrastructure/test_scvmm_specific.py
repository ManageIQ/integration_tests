# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.infrastructure.provider.scvmm import SCVMMProvider


@pytest.fixture
def testing_vm_without_dvd(provider, small_template):
    vm_name = "test_no_dvd_{}".format(fauxfactory.gen_alpha())
    vm = provider.appliance.collections.infra_vms.instantiate(
        vm_name, provider, small_template.name)
    vm.create_on_provider()
    vm.mgmt.disconnect_dvd_drives()
    yield vm
    vm.cleanup_on_provider()


@pytest.mark.meta(blockers=[1178961])
@pytest.mark.provider([SCVMMProvider], scope="module")
def test_no_dvd_ruins_refresh(provider, testing_vm_without_dvd):
    provider.refresh_provider_relationships()
    testing_vm_without_dvd.wait_to_appear()
