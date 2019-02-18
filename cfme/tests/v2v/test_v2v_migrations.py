"""Test to validate End-to-End migrations- functional testing."""
import fauxfactory
import pytest

from cfme.fixtures.provider import dportgroup_template
from cfme.fixtures.provider import dual_disk_template
from cfme.fixtures.provider import dual_network_template
from cfme.fixtures.provider import rhel69_template
from cfme.fixtures.provider import rhel7_minimal
from cfme.fixtures.provider import ubuntu16_template
from cfme.fixtures.provider import win10_template
from cfme.fixtures.provider import win2012_template
from cfme.fixtures.provider import win2016_template
from cfme.fixtures.provider import win7_template
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.ignore_stream('5.8'),
    pytest.mark.provider(
        classes=[RHEVMProvider],
        selector=ONE_PER_VERSION,
        required_flags=['v2v'],
        scope="module"
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_VERSION,
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


@pytest.mark.parametrize('form_data_vm_obj_single_datastore', [['nfs', 'nfs', rhel7_minimal],
                            ['nfs', 'iscsi', rhel7_minimal], ['iscsi', 'iscsi', rhel7_minimal],
                            ['iscsi', 'nfs', rhel7_minimal], ['iscsi', 'local', rhel7_minimal]],
                        indirect=True)
def test_single_datastore_single_vm_migration(request, appliance, v2v_providers, host_creds,
                                            conversion_tags,
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
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)
    # vm_obj is a list, with only 1 VM object, hence [0]
    src_vm_obj = form_data_vm_obj_single_datastore.vm_list[0]

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore.vm_list, start_migration=True)

    # explicit wait for spinner of in-progress status card
    view = appliance.browser.create_view(
        navigator.get_class(migration_plan_collection, 'All').VIEW.pick())
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=5, num_sec=150,
        handle_exception=True, fail_cond=False)

    # wait until plan is in progress
    wait_for(func=view.plan_in_progress, func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=5, num_sec=1800)
    view.switch_to("Completed Plans")
    view.wait_displayed()
    migration_plan_collection.find_completed_plan(migration_plan)
    logger.info("For plan %s, migration status after completion: %s, total time elapsed: %s",
        migration_plan.name, view.migration_plans_completed_list.get_vm_count_in_plan(
            migration_plan.name), view.migration_plans_completed_list.get_clock(
            migration_plan.name))
    # validate MAC address matches between source and target VMs
    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan.name)
    migrated_vm = get_migrated_vm_obj(src_vm_obj, v2v_providers.rhv_provider)
    assert src_vm_obj.mac_address == migrated_vm.mac_address


@pytest.mark.parametrize('form_data_vm_obj_single_network', [['DPortGroup', 'ovirtmgmt',
                            dportgroup_template], ['VM Network', 'ovirtmgmt', rhel7_minimal]],
                        indirect=True)
def test_single_network_single_vm_migration(request, appliance, v2v_providers, host_creds,
                                            conversion_tags,
                                            form_data_vm_obj_single_network):
    """
    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1/4h
        subcomponent: RHV
        upstream: yes
    """
    # This test will make use of migration request details page to track status of migration
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_network.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_network.vm_list, start_migration=True)
    # as migration is started, try to track progress using migration plan request details page
    view = appliance.browser.create_view(
        navigator.get_class(migration_plan_collection, 'All').VIEW.pick())
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=5, num_sec=150,
        handle_exception=True, fail_cond=False)
    view.progress_card.select_plan(migration_plan.name)
    view = appliance.browser.create_view(navigator.get_class(migration_plan_collection,
                                                             'Details').VIEW, wait='10s')
    request_details_list = view.migration_request_details_list
    vms = request_details_list.read()
    # ideally this will always pass as request details list shows VMs in migration plan
    # unless we have a bug
    assert len(vms) > 0, "No VMs displayed on Migration Plan Request Details list."

    wait_for(func=view.plan_in_progress, message="migration plan is in progress, be patient please",
     delay=5, num_sec=2700)
    assert (request_details_list.is_successful(vms[0]) and
        not request_details_list.is_errored(vms[0]))
    # validate MAC address matches between source and target VMs
    src_vm = form_data_vm_obj_single_network.vm_list.pop()
    migrated_vm = get_migrated_vm_obj(src_vm, v2v_providers.rhv_provider)
    assert src_vm.mac_address == migrated_vm.mac_address


@pytest.mark.parametrize(
    'form_data_dual_vm_obj_dual_datastore', [[['nfs', 'nfs',
    rhel7_minimal], ['iscsi', 'iscsi', rhel7_minimal]]],
    indirect=True
)
def test_dual_datastore_dual_vm_migration(request, appliance, v2v_providers, host_creds,
                                        conversion_tags,
                                        form_data_dual_vm_obj_dual_datastore, soft_assert):
    """
    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1/4h
        subcomponent: RHV
        upstream: yes
    """
    # This test will make use of migration request details page to track status of migration
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_dual_vm_obj_dual_datastore.
                                                       form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_dual_vm_obj_dual_datastore.vm_list, start_migration=True)
    # as migration is started, try to track progress using migration plan request details page
    view = appliance.browser.create_view(
        navigator.get_class(migration_plan_collection, 'All').VIEW.pick())
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=5, num_sec=150,
        handle_exception=True, fail_cond=False)
    view.progress_card.select_plan(migration_plan.name)
    view = appliance.browser.create_view(navigator.get_class(migration_plan_collection,
                                                             'Details').VIEW, wait='10s')
    request_details_list = view.migration_request_details_list
    vms = request_details_list.read()

    wait_for(func=view.plan_in_progress, message="migration plan is in progress, be patient please",
     delay=5, num_sec=1800)

    for vm in vms:
        soft_assert(request_details_list.is_successful(vm) and
         not request_details_list.is_errored(vm))

    src_vms_list = form_data_dual_vm_obj_dual_datastore.vm_list
    # validate MAC address matches between source and target VMs
    for src_vm in src_vms_list:
        migrated_vm = get_migrated_vm_obj(src_vm, v2v_providers.rhv_provider)
        soft_assert(src_vm.mac_address == migrated_vm.mac_address)


@pytest.mark.parametrize(
    'form_data_vm_obj_dual_nics', [[['VM Network', 'ovirtmgmt'],
    ['DPortGroup', 'Storage - VLAN 33'], dual_network_template]],
    indirect=True
)
def test_dual_nics_migration(request, appliance, v2v_providers, host_creds, conversion_tags,
         form_data_vm_obj_dual_nics):
    """
    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1/4h
        subcomponent: RHV
        upstream: yes
    """
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_dual_nics.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_vm_obj_dual_nics.vm_list, start_migration=True)

    # explicit wait for spinner of in-progress status card
    view = appliance.browser.create_view(
        navigator.get_class(migration_plan_collection, 'All').VIEW.pick())
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=5, num_sec=150,
        handle_exception=True, fail_cond=False)

    # wait until plan is in progress
    wait_for(func=view.plan_in_progress, func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=5, num_sec=2700)

    view.switch_to("Completed Plans")
    view.wait_displayed()
    migration_plan_collection.find_completed_plan(migration_plan)
    logger.info("For plan %s, migration status after completion: %s, total time elapsed: %s",
        migration_plan.name, view.migration_plans_completed_list.get_vm_count_in_plan(
            migration_plan.name), view.migration_plans_completed_list.get_clock(
            migration_plan.name))
    migration_plan_collection.find_completed_plan(migration_plan)
    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan.name)
    # validate MAC address matches between source and target VMs
    src_vm = form_data_vm_obj_dual_nics.vm_list.pop()
    migrated_vm = get_migrated_vm_obj(src_vm, v2v_providers.rhv_provider)
    assert set(src_vm.mac_address.split(", ")) == set(migrated_vm.mac_address.split(", "))


@pytest.mark.parametrize('form_data_vm_obj_single_datastore', [['nfs', 'nfs', dual_disk_template]],
                        indirect=True)
def test_dual_disk_vm_migration(request, appliance, v2v_providers, host_creds, conversion_tags,
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
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore.vm_list, start_migration=True)
    # explicit wait for spinner of in-progress status card
    view = appliance.browser.create_view(
        navigator.get_class(migration_plan_collection, 'All').VIEW.pick())
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=5, num_sec=150,
        handle_exception=True, fail_cond=False)

    # wait until plan is in progress
    wait_for(func=view.plan_in_progress, func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=5, num_sec=3600)

    view.switch_to("Completed Plans")
    view.wait_displayed()
    migration_plan_collection.find_completed_plan(migration_plan)
    logger.info("For plan %s, migration status after completion: %s, total time elapsed: %s",
        migration_plan.name, view.migration_plans_completed_list.get_vm_count_in_plan(
            migration_plan.name), view.migration_plans_completed_list.get_clock(
            migration_plan.name))
    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan.name)
    # validate MAC address matches between source and target VMs
    src_vm = form_data_vm_obj_single_datastore.vm_list.pop()
    migrated_vm = get_migrated_vm_obj(src_vm, v2v_providers.rhv_provider)
    assert src_vm.mac_address == migrated_vm.mac_address


@pytest.mark.parametrize('form_data_multiple_vm_obj_single_datastore', [['nfs', 'nfs',
                        [win7_template, win10_template]], ['nfs', 'nfs',
                        [win2016_template, rhel69_template]], ['nfs', 'nfs',
                        [win2012_template, ubuntu16_template]]], indirect=True)
def test_migrations_different_os_templates(request, appliance, v2v_providers, host_creds,
                                    conversion_tags,
                                    form_data_multiple_vm_obj_single_datastore,
                                    soft_assert):
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
    view = appliance.browser.create_view(
        navigator.get_class(migration_plan_collection, 'All').VIEW.pick())
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=5, num_sec=150,
        handle_exception=True, fail_cond=False)
    view.progress_card.select_plan(migration_plan.name)
    view = appliance.browser.create_view(navigator.get_class(migration_plan_collection,
                                                             'Details').VIEW, wait='10s')
    request_details_list = view.migration_request_details_list
    view.items_on_page.item_select('15')
    vms = request_details_list.read()

    wait_for(func=view.plan_in_progress, message="migration plan is in progress, be patient please",
     delay=5, num_sec=4200)

    for vm in vms:
        soft_assert(request_details_list.is_successful(vm) and
         not request_details_list.is_errored(vm))

    src_vms_list = form_data_multiple_vm_obj_single_datastore.vm_list
    # validate MAC address matches between source and target VMs
    for src_vm in src_vms_list:
        migrated_vm = get_migrated_vm_obj(src_vm, v2v_providers.rhv_provider)
        soft_assert(src_vm.mac_address == migrated_vm.mac_address)


@pytest.mark.parametrize('conversion_tags, form_data_vm_obj_single_datastore', [['SSH',
    ['nfs', 'nfs', rhel7_minimal]]], indirect=True)
def test_single_vm_migration_with_ssh(request, appliance, v2v_providers, host_creds,
                                    conversion_tags,
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
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore.vm_list, start_migration=True)

    # explicit wait for spinner of in-progress status card
    view = appliance.browser.create_view(
        navigator.get_class(migration_plan_collection, 'All').VIEW.pick())
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=5, num_sec=150,
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
    # validate MAC address matches between source and target VMs
    src_vm = form_data_vm_obj_single_datastore.vm_list.pop()
    migrated_vm = get_migrated_vm_obj(src_vm, v2v_providers.rhv_provider)
    assert src_vm.mac_address == migrated_vm.mac_address
