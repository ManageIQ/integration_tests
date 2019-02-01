"""Test contains all post migration usecases"""
import fauxfactory
import pytest
import re

from cfme.base.login import BaseLoggedInPage
from cfme.fixtures.provider import rhel7_minimal
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION, ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to, navigator
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError, wait_for


pytestmark = [
    pytest.mark.provider(
        classes=[RHEVMProvider],
        selector=ONE_PER_VERSION,
        required_flags=['v2v'],
        scope="module"
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_TYPE,
        fixture_name='source_provider',
        required_flags=['v2v'],
        scope="module"
    )
]


def get_migrated_vm_obj(src_vm_obj, target_provider):
    """Returns the migrated_vm obj from target_provider."""
    collection = target_provider.appliance.provider_based_collection(target_provider)
    migrated_vm = collection.instantiate(src_vm_obj.name, target_provider)
    return migrated_vm


def test_migration_policy_tag(request, appliance, v2v_providers, host_creds, conversion_tags,
                              form_data_vm_map_obj_mini, soft_assert):
    """Test policy to prevent source VM from starting if migration is complete

    Polarion:
        assignee: ytale
        initialEstimate: 1/4h
        casecomponent: V2V
    """
    migration_plan_collection = appliance.collections.v2v_plans
    # vm_obj is a list, with only 1 VM object, hence [0]
    vm_obj = form_data_vm_map_obj_mini.vm_list[0]
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=form_data_vm_map_obj_mini.map_obj.name,
        vm_list=form_data_vm_map_obj_mini.vm_list,
        start_migration=True
    )

    # explicit wait for spinner of in-progress status card
    view = appliance.browser.create_view(
        navigator.get_class(migration_plan_collection, "All").VIEW.pick()
    )
    wait_for(
        func=view.progress_card.is_plan_started,
        func_args=[migration_plan.name],
        message="migration plan is starting, be patient please",
        delay=5,
        num_sec=150,
        handle_exception=True,
        fail_cond=False
    )

    # wait until plan is in progress
    wait_for(
        func=view.plan_in_progress,
        func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=15,
        num_sec=3600
    )
    view.switch_to("Completed Plans")
    view.wait_displayed()
    migration_plan_collection.find_completed_plan(migration_plan)

    logger.info("For plan {plan_name}, migration status : {count}, total time elapsed: {clock}"
                .format(plan_name=migration_plan.name,
                count=view.migration_plans_completed_list.get_vm_count_in_plan(migration_plan.name),
                clock=view.migration_plans_completed_list.get_clock(migration_plan.name)))

    available_tags = vm_obj.get_tags()
    soft_assert("Migrated" in [tag.display_name for tag in available_tags])

    vm_obj.wait_for_vm_state_change(desired_state=vm_obj.STATE_OFF, timeout=720)
    vm_obj.power_control_from_cfme(option=vm_obj.POWER_ON, cancel=False)
    view = appliance.browser.create_view(BaseLoggedInPage)
    view.flash.assert_success_message(text="Start initiated", partial=True)
    try:
        vm_obj.wait_for_vm_state_change(desired_state=vm_obj.STATE_ON, timeout=120)
    except TimedOutError:
        pass
    vm_state = vm_obj.find_quadicon().data["state"]
    soft_assert(vm_state == "off")


@pytest.mark.parametrize(
    "form_data_vm_obj_single_datastore", [["nfs", "nfs", rhel7_minimal]], indirect=True
)
def test_migrations_vm_attributes(request, appliance, v2v_providers, host_creds, conversion_tags,
                                  form_data_vm_obj_single_datastore):
    """Tests cpu, socket, core, memory attributes on migrated vm"""
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(
        form_data_vm_obj_single_datastore.form_data
    )

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    # vm_obj is a list, with only 1 VM object, hence [0]
    src_vm_obj = form_data_vm_obj_single_datastore.vm_list[0]
    source_view = navigate_to(src_vm_obj, "Details")
    summary = source_view.entities.summary("Properties").get_text_of("Container")
    source_cpu, source_socket, source_core, source_memory = re.findall("\d+", summary)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore.vm_list,
        start_migration=True
    )

    # explicit wait for spinner of in-progress status card
    view = appliance.browser.create_view(
        navigator.get_class(migration_plan_collection, "All").VIEW.pick()
    )
    wait_for(
        func=view.progress_card.is_plan_started,
        func_args=[migration_plan.name],
        message="migration plan is starting, be patient please",
        delay=5,
        num_sec=150,
        handle_exception=True
    )

    # wait until plan is in progress
    wait_for(
        func=view.plan_in_progress,
        func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=5,
        num_sec=1800
    )
    view.switch_to("Completed Plans")
    view.wait_displayed()
    migration_plan_collection.find_completed_plan(migration_plan)
    logger.info(
        "For plan %s, migration status after completion: %s, total time elapsed: %s",
        migration_plan.name,
        view.migration_plans_completed_list.get_vm_count_in_plan(migration_plan.name),
        view.migration_plans_completed_list.get_clock(migration_plan.name))

    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan.name)
    view = navigate_to(get_migrated_vm_obj(src_vm_obj, v2v_providers.rhv_provider), "Details")
    summary = view.entities.summary("Properties").get_text_of("Container")
    target_cpu, target_socket, target_core, target_memory = re.findall("\d+", summary)
    # cpu on source and target vm
    assert source_cpu == target_cpu
    # sockets on source and target vm
    assert source_socket == target_socket
    # core on source and target vm
    assert source_core == target_core
    # memory on source and target vm
    assert source_memory == target_memory
