import time

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.templates import Templates
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import wait_for

pytestmark = [
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
    pytest.mark.usefixtures("v2v_provider_setup"),
    test_requirements.v2v
]


@pytest.fixture(scope="function")
def cancel_migration_plan(appliance, provider, mapping_data_vm_obj_mini):
    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(15, start="plan_desc_"),
        infra_map=mapping_data_vm_obj_mini.infra_mapping_data.get("name"),
        target_provider=provider,
        vm_list=mapping_data_vm_obj_mini.vm_list
    )
    if migration_plan.wait_for_state("Started"):
        request_details_list = migration_plan.get_plan_vm_list(wait_for_migration=False)
        vms = request_details_list.read()
        # Random percentage to cancel migration at
        cancel_migration_after_percent = 6

        def _get_plan_status_and_cancel():
            migration_plan_in_progress_tracker = []
            for vm in vms:
                clock_reading1 = request_details_list.get_clock(vm)
                time.sleep(1)  # wait 1 sec to see if clock is ticking
                if request_details_list.progress_percent(vm) > cancel_migration_after_percent:
                    request_details_list.cancel_migration(vm, confirmed=True)
                clock_reading2 = request_details_list.get_clock(vm)
                migration_plan_in_progress_tracker.append(request_details_list.is_in_progress(vm)
                                                          and (clock_reading1 < clock_reading2))
            return not any(migration_plan_in_progress_tracker)

        wait_for(func=_get_plan_status_and_cancel, message="migration plan is in progress,"
                 "be patient please", delay=5, num_sec=3600)
    else:
        pytest.skip("Migration plan failed to start")
    yield migration_plan
    migration_plan.delete_completed_plan()


@pytest.mark.tier(1)
@pytest.mark.parametrize('source_type, dest_type, template_type',
                         [['nfs', 'nfs', [Templates.RHEL7_MINIMAL,
                                          Templates.RHEL7_MINIMAL]]])
def test_dual_vm_cancel_migration(request, appliance, soft_assert, provider,
                                  source_type, dest_type, template_type,
                                  mapping_data_multiple_vm_obj_single_datastore):
    """
    Polarion:
        assignee: sshveta
        initialEstimate: 1/2h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
        testSteps:
            1. Add source and target provider
            2. Create infra map and migration plan
            3. Start migration plan and cancel.
    """
    # This test will make use of migration request details page to track status of migration
    cancel_migration_after_percent = 20
    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping_data = mapping_data_multiple_vm_obj_single_datastore.infra_mapping_data
    mapping = infrastructure_mapping_collection.create(**mapping_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(start="plan_desc_"),
        infra_map=mapping.name,
        target_provider=provider,
        vm_list=mapping_data_multiple_vm_obj_single_datastore.vm_list,
    )

    assert migration_plan.wait_for_state("Started")
    request_details_list = migration_plan.get_plan_vm_list(wait_for_migration=False)
    vms = request_details_list.read()

    def _get_plan_status_and_cancel():
        migration_plan_in_progress_tracker = []
        for vm in vms:
            clock_reading1 = request_details_list.get_clock(vm)
            time.sleep(1)  # wait 1 sec to see if clock is ticking
            if request_details_list.progress_percent(vm) > cancel_migration_after_percent:
                request_details_list.cancel_migration(vm, confirmed=True)
            clock_reading2 = request_details_list.get_clock(vm)
            migration_plan_in_progress_tracker.append(request_details_list.is_in_progress(vm) and
              (clock_reading1 < clock_reading2))
        return not any(migration_plan_in_progress_tracker)

    wait_for(func=_get_plan_status_and_cancel, message="migration plan is in progress,"
             "be patient please", delay=5, num_sec=3600)

    for vm in vms:
        soft_assert(request_details_list.is_cancelled(vm))
        soft_assert(request_details_list.progress_percent(vm) < 100.0 or
                    "Virtual machine migrated" not in request_details_list.get_message_text(vm))


@pytest.mark.tier(2)
@pytest.mark.parametrize(
    "source_type, dest_type, template_type",
    [["nfs", "nfs", Templates.RHEL7_MINIMAL]])
def test_cancel_migration_attachments(
        request, appliance, soft_assert, provider,
        source_type, dest_type, template_type,
        mapping_data_vm_obj_single_datastore):
    """
    Test to cancel migration and check attached instance, volume and port is removed from provider
    Polarion:
        assignee: sshveta
        initialEstimate: 1/2h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
    """
    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping_data = mapping_data_vm_obj_single_datastore.infra_mapping_data
    mapping = infrastructure_mapping_collection.create(**mapping_data)
    vm_obj = mapping_data_vm_obj_single_datastore.vm_list[0]

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(15, start="plan_desc_"),
        infra_map=mapping.name,
        target_provider=provider,
        vm_list=[vm_obj])

    migration_plan.wait_for_state("In_Progress")
    request_details_list = migration_plan.get_plan_vm_list(wait_for_migration=False)
    vm_detail = request_details_list.read()[0]
    request_details_list.cancel_migration(vm_detail, confirmed=True)  # Cancel migration

    def get_plan_status_and_cancel():
        return not request_details_list.is_in_progress(vm_detail)

    wait_for(
        func=get_plan_status_and_cancel,
        delay=10,
        num_sec=600,
        message="migration plan is in progress, be patient please")

    soft_assert(request_details_list.is_cancelled(vm_detail))
    soft_assert(request_details_list.progress_percent(vm_detail) < 100.0 or
                "Virtual machine migrated" not in request_details_list.get_message_text(vm_detail))

    vm_on_dest = provider.mgmt.find_vms(name=vm_obj.name)
    # Test1: Check if instance is on openstack/rhevm provider
    soft_assert(not vm_on_dest)

    if provider.one_of(OpenStackProvider) and vm_on_dest:
        # Test2: Check if instance has any volumes attached
        server = provider.mgmt.get_vm(name=vm_obj.name)
        soft_assert(not server.attached_volumes)

        # Test3: Check if instance has any ports attached
        soft_assert(provider.mgmt.get_ports(uuid=server.uuid))


@pytest.mark.tier(1)
@pytest.mark.meta(blockers=[BZ(1746592)], automates=[1755632])
def test_retry_migration_plan(cancel_migration_plan):
    """
    Test to cancel migration and then retry migration
    Polarion:
        assignee: sshveta
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V

    Bugzilla:
        1755632
        1746592
    """
    migration_plan = cancel_migration_plan
    view = navigate_to(migration_plan, "Complete")
    # Retry Migration
    view.plans_completed_list.migrate_plan(migration_plan.name)
    assert migration_plan.wait_for_state("Started")

    # Automating BZ 1755632
    retry_interval_log = LogValidator(
        '/var/www/miq/vmdb/log/evm.log',
        matched_patterns=[r'.*to Automate for delivery in \[60\] seconds.*']
    )
    retry_interval_log.start_monitoring()
    # search logs and wait for validation
    assert (retry_interval_log.validate(wait="150s"))

    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")
