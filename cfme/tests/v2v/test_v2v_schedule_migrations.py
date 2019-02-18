"""Test to validate basic navigations.Later to be replaced with End-to-End functional testing."""
import fauxfactory
import pytest

from cfme.fixtures.provider import rhel7_minimal
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

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


@pytest.mark.parametrize('form_data_vm_obj_single_datastore', [['nfs', 'nfs', rhel7_minimal]],
 indirect=True)
def test_single_vm_scheduled_migration(request, appliance, v2v_providers, host_creds,
                                    conversion_tags, soft_assert,
                                    form_data_vm_obj_single_datastore):
    """
    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1/4h
        subcomponent: RHV
        upstream: yes
    """
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(
        form_data_vm_obj_single_datastore.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore.vm_list, start_migration=False)
    view = navigate_to(migration_plan_collection, 'All')

    # Test scheduled Migration
    view.migration_plans_not_started_list.schedule_migration(migration_plan.name, after_mins=3)
    soft_assert('Migration scheduled' in view.migration_plans_not_started_list.
        get_clock(migration_plan.name))
    view.migration_plans_not_started_list.schedule_migration(migration_plan.name)
    soft_assert(view.migration_plans_not_started_list.get_clock(migration_plan.name) is '')
    view.migration_plans_not_started_list.schedule_migration(migration_plan.name, after_mins=3)
    view.switch_to('In Progress Plans')
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=30, num_sec=600,
        handle_exception=True, fail_cond=False)

    # wait until plan is in progress
    wait_for(func=view.plan_in_progress, func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=5, num_sec=1800)

    view.switch_to("Completed Plans")
    view.wait_displayed()
    migration_plan_collection.find_completed_plan(migration_plan)
    logger.info("For plan %s, migration status after completion: %s, total time elapsed: %s",
        migration_plan.name,
        view.migration_plans_completed_list.get_vm_count_in_plan(migration_plan.name),
        view.migration_plans_completed_list.get_clock(migration_plan.name))
    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan.name)
