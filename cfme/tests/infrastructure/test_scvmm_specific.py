# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.vm import VM
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.utils import testgen


pytest_generate_tests = testgen.generate([SCVMMProvider], scope="module")


@pytest.mark.meta(blockers=[1178961])
@pytest.mark.uncollectif(
    lambda provider: "host_group" in provider.data.get("provisioning", {}),
    reason="No host group")
def test_no_dvd_ruins_refresh(provider, small_template):
    host_group = provider.data["provisioning"]["host_group"]
    with provider.mgmt.with_vm(
            small_template.name,
            vm_name="test_no_dvd_{}".format(fauxfactory.gen_alpha()),
            host_group=host_group) as vm_name:
        provider.mgmt.disconnect_dvd_drives(vm_name)
        vm = VM.factory(vm_name, provider)
        provider.refresh_provider_relationships()
        vm.wait_to_appear()
