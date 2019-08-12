"""Tests to validate post-migrations usecases"""
import re

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.common import BaseLoggedInPage
from cfme.fixtures.v2v_fixtures import get_migrated_vm
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import TimedOutError

pytestmark = [
    test_requirements.v2v,
    pytest.mark.provider(
        classes=[RHEVMProvider, OpenStackProvider],
        selector=ONE_PER_VERSION,
        required_flags=["v2v"],
        scope="module",
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_TYPE,
        required_flags=["v2v"],
        fixture_name="source_provider",
        scope="module",
    ),
    pytest.mark.usefixtures("v2v_provider_setup")
]


@pytest.mark.tier(1)
def test_migration_post_attribute(appliance, provider, mapping_data_vm_obj_mini, soft_assert):
    """
    Test to validate v2v post-migrations usecases

    Polarion:
        assignee: sshveta
        initialEstimate: 1/4h
        caseimportance: critical
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
        testSteps:
            1. Add source and target provider
            2. Create infra map and migration plan
            3. Migrate VM
            4. Check vm attributes upon successful migration
    """
    src_vm_obj = mapping_data_vm_obj_mini.vm_list[0]
    source_view = navigate_to(src_vm_obj, "Details")
    summary = source_view.entities.summary("Properties").get_text_of("Container")
    source_cpu, source_socket, source_core, source_memory = re.findall(r"\d+", summary)
    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping_data_vm_obj_mini.infra_mapping_data.get("name"),
        target_provider=provider,
        vm_list=mapping_data_vm_obj_mini.vm_list
    )
    assert migration_plan.wait_for_state("Started")
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")

    migrated_vm = get_migrated_vm(src_vm_obj, provider)

    # Test1: mac address matches between source and target vm
    soft_assert(src_vm_obj.mac_address == migrated_vm.mac_address)

    # Test2: policy tag for migrated vm
    available_tags = src_vm_obj.get_tags()
    soft_assert("Migrated" in [tag.display_name for tag in available_tags])

    # Test3: policy to prevent source vm from starting if migration is completed
    src_vm_obj.wait_for_vm_state_change(desired_state=src_vm_obj.STATE_OFF, timeout=720)
    src_vm_obj.power_control_from_cfme(option=src_vm_obj.POWER_ON, cancel=False)
    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_success_message(text="Start initiated", partial=True)
    try:
        src_vm_obj.wait_for_vm_state_change(desired_state=src_vm_obj.STATE_ON, timeout=120)
    except TimedOutError:
        pass
    vm_state = src_vm_obj.find_quadicon().data["state"]
    soft_assert(vm_state == "off")

    target_view = navigate_to(migrated_vm, "Details")
    summary = target_view.entities.summary("Properties").get_text_of("Container")
    target_cpu, target_socket, target_core, target_memory = re.findall(r"\d+", summary)
    # Test4: cpu on source and target vm
    soft_assert(source_cpu == target_cpu)
    # Test5: sockets on source and target vm
    soft_assert(source_socket == target_socket)
    # Test6: cores on source and target vm
    soft_assert(source_core == target_core)
    # Test7: memory on source and target vm
    soft_assert(source_memory == target_memory)
