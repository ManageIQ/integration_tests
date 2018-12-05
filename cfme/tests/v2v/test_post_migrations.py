"""Test contains all post migration usecases"""
import fauxfactory
import pytest

from cfme.base.login import BaseLoggedInPage
from cfme.fixtures.provider import rhel7_minimal
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError, wait_for

pytestmark = [
    pytest.mark.provider(
        classes=[RHEVMProvider],
        selector=ONE_PER_VERSION,
        required_flags=['v2v']
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_VERSION,
        fixture_name='second_provider',
        required_flags=['v2v']
    )
]


def get_migrated_vm_obj(src_vm_obj, target_provider):
    """Returns the migrated_vm obj from target_provider."""
    collection = target_provider.appliance.provider_based_collection(target_provider)
    migrated_vm = collection.instantiate(src_vm_obj.name, target_provider)
    return migrated_vm


@pytest.mark.parametrize(
    "form_data_vm_obj_single_datastore", [["nfs", "nfs", rhel7_minimal]], indirect=True
)
def test_migration_policy_tag(request, appliance, v2v_providers, host_creds, conversion_tags,
                              form_data_vm_obj_single_datastore, soft_assert):
    """Test policy to prevent source VM from starting if migration is complete

    Polarion:
        assignee: None
        initialEstimate: None
    """
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    # vm_obj is a list, with only 1 VM object, hence [0]
    vm_obj = form_data_vm_obj_single_datastore.vm_list[0]
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore.vm_list,
        start_migration=True,
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
    )

    # wait until plan is in progress
    wait_for(
        func=view.plan_in_progress,
        func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=15,
        num_sec=3600,
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
