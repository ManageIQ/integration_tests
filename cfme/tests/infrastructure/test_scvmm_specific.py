# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.infrastructure.provider.scvmm import SCVMMProvider


@pytest.mark.meta(blockers=[1178961])
@pytest.mark.uncollectif(
    lambda provider: "host_group" in provider.data.get("provisioning", {}),
    reason="No host group")
@pytest.mark.provider([SCVMMProvider], scope="module")
def test_no_dvd_ruins_refresh(provider, small_template):
    host_group = provider.data["provisioning"]["host_group"]
    with provider.mgmt.with_vm(
            small_template.name,
            vm_name="test_no_dvd_{}".format(fauxfactory.gen_alpha()),
            host_group=host_group) as vm_name:
        provider.mgmt.disconnect_dvd_drives(vm_name)
        vm = provider.appliance.collections.infra_vms.instantiate(vm_name,
                                                                  provider,
                                                                  small_template.name)
        provider.refresh_provider_relationships()
        vm.wait_to_appear()
