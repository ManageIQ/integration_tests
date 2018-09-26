"""Test to validate basic navigations.Later to be replaced with End-to-End functional testing."""
import fauxfactory
import pytest
import time

from cfme.fixtures.provider import rhel7_minimal
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

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


@pytest.mark.parametrize('form_data_multiple_vm_obj_single_datastore', [['nfs', 'nfs',
    [rhel7_minimal, rhel7_minimal]]],
    indirect=True)
@pytest.mark.parametrize('cancel_migration_after_percent', [1, 10, 50, 80])
def test_dual_vm_migration_cancel_migration(request, appliance, v2v_providers, host_creds,
                                        conversion_tags,
                                        form_data_multiple_vm_obj_single_datastore, soft_assert,
                                        cancel_migration_after_percent):
    # TODO: Improve this test to cover cancel operation at various stages in migration.
    # This test will make use of migration request details page to track status of migration
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(
        form_data_multiple_vm_obj_single_datastore.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_multiple_vm_obj_single_datastore.vm_list, start_migration=True)
    # as migration is started, try to track progress using migration plan request details page
    view = appliance.browser.create_view(navigator.get_class(migration_plan_collection, 'All').VIEW)
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=5, num_sec=150,
        handle_exception=True)
    view.progress_card.select_plan(migration_plan.name)
    view = appliance.browser.create_view(navigator.get_class(migration_plan_collection,
                                                             'Details').VIEW)
    view.wait_displayed()
    request_details_list = view.migration_request_details_list
    vms = request_details_list.read()

    def _get_plan_status_and_cancel():
        migration_plan_in_progress_tracker = []
        for vm in vms:
            clock_reading1 = request_details_list.get_clock(vm)
            time.sleep(1)  # wait 1 sec to see if clock is ticking
            logger.info("For vm %s, current message is %s", vm,
                request_details_list.get_message_text(vm))
            current_progress_text = request_details_list.get_progress_description(vm)
            if request_details_list.progress_percent(vm) > cancel_migration_after_percent:
                request_details_list.cancel_migration(vm, confirmed=True)
            logger.info("For vm %s, current progress description is %s", vm,
                current_progress_text)
            clock_reading2 = request_details_list.get_clock(vm)
            logger.info("clock_reading1: %s, clock_reading2:%s", clock_reading1, clock_reading2)
            logger.info("For vm %s, is currently in progress: %s", vm,
              request_details_list.is_in_progress(vm))
            migration_plan_in_progress_tracker.append(request_details_list.is_in_progress(vm) and
              (clock_reading1 < clock_reading2))
        return not any(migration_plan_in_progress_tracker)

    wait_for(func=_get_plan_status_and_cancel, message="migration plan is in progress,"
        "be patient please", delay=5, num_sec=3600)

    for vm in vms:
        soft_assert(request_details_list.is_cancelled(vm))
