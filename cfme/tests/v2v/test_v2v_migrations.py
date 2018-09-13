"""Test to validate End-to-End migrations- functional testing."""
import fauxfactory
import pytest

from cfme.fixtures.provider import (dual_network_template, dual_disk_template,
 dportgroup_template, win7_template, win10_template, win2016_template, rhel69_template,
 win2012_template, ubuntu16_template, rhel7_minimal)
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
        required_flags=['v2v']
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_VERSION,
        fixture_name='second_provider',
        required_flags=['v2v']
    )
]


@pytest.mark.parametrize('form_data_vm_obj_single_datastore', [['nfs', 'nfs', rhel7_minimal],
                            ['nfs', 'iscsi', rhel7_minimal], ['iscsi', 'iscsi', rhel7_minimal],
                            ['iscsi', 'nfs', rhel7_minimal], ['iscsi', 'local', rhel7_minimal]],
                        indirect=True)
def test_single_datastore_single_vm_migration(request, appliance, v2v_providers, host_creds,
                                            conversion_tags,
                                            form_data_vm_obj_single_datastore):
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    # form_data_vm_obj_single_datastore has form_data at [0]
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore[0])

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    src_vm_obj = form_data_vm_obj_single_datastore[1][0]
    wait_for(lambda: src_vm_obj.ip_address is not None,
        message="Waiting for VM to display IP in CFME",
        fail_func=src_vm_obj.refresh_relationships,
        delay=5, timeout=300)

    src_vm_ip_addr = src_vm_obj.ip_address

    migration_plan_collection = appliance.collections.v2v_plans
    # form_data_vm_obj_single_datastore has vm_obj list at [1]
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore[1], start_migration=True)

    # explicit wait for spinner of in-progress status card
    view = appliance.browser.create_view(navigator.get_class(migration_plan_collection, 'All').VIEW)
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=5, num_sec=150,
        handle_exception=True)

    # wait until plan is in progress
    wait_for(func=view.plan_in_progress, func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=5, num_sec=1800)

    view.migr_dropdown.item_select("Completed Plans")
    view.wait_displayed()
    logger.info("For plan %s, migration status after completion: %s, total time elapsed: %s",
        migration_plan.name, view.migration_plans_completed_list.get_vm_count_in_plan(
            migration_plan.name), view.migration_plans_completed_list.get_clock(
            migration_plan.name))
    # validate MAC address matches between source and target VMs
    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan.name)
    src_vm = form_data_vm_obj_single_datastore[1][0]
    rhv_prov = v2v_providers[1]
    collection = rhv_prov.appliance.provider_based_collection(rhv_prov)
    migrated_vm = collection.instantiate(src_vm.name, rhv_prov)
    assert src_vm.mac_address == migrated_vm.mac_address
    assert src_vm_ip_addr == migrated_vm.ip_address


@pytest.mark.parametrize('form_data_vm_obj_single_network', [['DPortGroup', 'ovirtmgmt',
                            dportgroup_template], ['VM Network', 'ovirtmgmt', rhel7_minimal]],
                        indirect=True)
def test_single_network_single_vm_migration(request, appliance, v2v_providers, host_creds,
                                            conversion_tags,
                                            form_data_vm_obj_single_network):
    # This test will make use of migration request details page to track status of migration
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    # form_data_vm_obj_single_network has form_data at [0]
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_network[0])

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    # form_data_vm_obj_single_network has list of vm_obj at [1]
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_network[1], start_migration=True)
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
    # ideally this will always pass as request details list shows VMs in migration plan
    # unless we have a bug
    assert len(vms) > 0, "No VMs displayed on Migration Plan Request Details list."

    wait_for(func=view.plan_in_progress, message="migration plan is in progress, be patient please",
     delay=5, num_sec=2700)
    assert (request_details_list.is_successful(vms[0]) and
        not request_details_list.is_errored(vms[0]))
    # validate MAC address matches between source and target VMs
    src_vm = form_data_vm_obj_single_network[1][0]
    rhv_prov = v2v_providers[1]
    collection = rhv_prov.appliance.provider_based_collection(rhv_prov)
    migrated_vm = collection.instantiate(src_vm.name, rhv_prov)
    assert src_vm.mac_address == migrated_vm.mac_address


@pytest.mark.parametrize(
    'form_data_dual_vm_obj_dual_datastore', [[['nfs', 'nfs',
    rhel7_minimal], ['iscsi', 'iscsi', rhel7_minimal]]],
    indirect=True
)
def test_dual_datastore_dual_vm_migration(request, appliance, v2v_providers, host_creds,
                                        conversion_tags,
                                        form_data_dual_vm_obj_dual_datastore, soft_assert):
    # This test will make use of migration request details page to track status of migration
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    # form_data_dual_vm_obj_dual_datastore has form_data at [0]
    mapping = infrastructure_mapping_collection.create(form_data_dual_vm_obj_dual_datastore[0])

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    # form_data_dual_vm_obj_dual_datastore has list of vm_obj at [1]
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_dual_vm_obj_dual_datastore[1], start_migration=True)
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

    wait_for(func=view.plan_in_progress, message="migration plan is in progress, be patient please",
     delay=5, num_sec=1800)

    for vm in vms:
        soft_assert(request_details_list.is_successful(vm) and
         not request_details_list.is_errored(vm))

    rhv_prov = v2v_providers[1]
    collection = rhv_prov.appliance.provider_based_collection(rhv_prov)
    # validate MAC address matches between source and target VMs
    for src_vm in form_data_dual_vm_obj_dual_datastore[1]:
        migrated_vm = collection.instantiate(src_vm.name, rhv_prov)
        soft_assert(src_vm.mac_address == migrated_vm.mac_address)


@pytest.mark.parametrize(
    'form_data_vm_obj_dual_nics', [[['VM Network', 'ovirtmgmt'],
    ['DPortGroup', 'Storage - VLAN 33'], dual_network_template]],
    indirect=True
)
def test_dual_nics_migration(request, appliance, v2v_providers, host_creds, conversion_tags,
         form_data_vm_obj_dual_nics):
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    # form_data_vm_obj_dual_nics has form_data at [0]
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_dual_nics[0])

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    # form_data_vm_obj_dual_nics has vm_obj at [1]
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_vm_obj_dual_nics[1], start_migration=True)

    # explicit wait for spinner of in-progress status card
    view = appliance.browser.create_view(navigator.get_class(migration_plan_collection, 'All').VIEW)
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=5, num_sec=150,
        handle_exception=True)

    # wait until plan is in progress
    wait_for(func=view.plan_in_progress, func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=5, num_sec=2700)

    view.migr_dropdown.item_select("Completed Plans")
    view.wait_displayed()
    logger.info("For plan %s, migration status after completion: %s, total time elapsed: %s",
        migration_plan.name, view.migration_plans_completed_list.get_vm_count_in_plan(
            migration_plan.name), view.migration_plans_completed_list.get_clock(
            migration_plan.name))
    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan.name)
    # validate MAC address matches between source and target VMs
    src_vm = form_data_vm_obj_dual_nics[1][0]
    rhv_prov = v2v_providers[1]
    collection = rhv_prov.appliance.provider_based_collection(rhv_prov)
    migrated_vm = collection.instantiate(src_vm.name, rhv_prov)
    assert src_vm.mac_address == migrated_vm.mac_address


@pytest.mark.parametrize('form_data_vm_obj_single_datastore', [['nfs', 'nfs', dual_disk_template]],
                        indirect=True)
def test_dual_disk_vm_migration(request, appliance, v2v_providers, host_creds, conversion_tags,
                                form_data_vm_obj_single_datastore):
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    # form_data_vm_obj_single_datastore has form_data at [0]
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore[0])

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    # form_data_vm_obj_single_datastore has vm_obj at [1]
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore[1], start_migration=True)
    # explicit wait for spinner of in-progress status card
    view = appliance.browser.create_view(navigator.get_class(migration_plan_collection, 'All').VIEW)
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=5, num_sec=150,
        handle_exception=True)

    # wait until plan is in progress
    wait_for(func=view.plan_in_progress, func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=5, num_sec=3600)

    view.migr_dropdown.item_select("Completed Plans")
    view.wait_displayed()
    logger.info("For plan %s, migration status after completion: %s, total time elapsed: %s",
        migration_plan.name, view.migration_plans_completed_list.get_vm_count_in_plan(
            migration_plan.name), view.migration_plans_completed_list.get_clock(
            migration_plan.name))
    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan.name)
    # validate MAC address matches between source and target VMs
    src_vm = form_data_vm_obj_single_datastore[1][0]
    rhv_prov = v2v_providers[1]
    collection = rhv_prov.appliance.provider_based_collection(rhv_prov)
    migrated_vm = collection.instantiate(src_vm.name, rhv_prov)
    assert src_vm.mac_address == migrated_vm.mac_address


@pytest.mark.parametrize('form_data_multiple_vm_obj_single_datastore', [['nfs', 'nfs',
                        [win7_template, win10_template]], ['nfs', 'nfs',
                        [win2016_template, rhel69_template]], ['nfs', 'nfs',
                        [win2012_template, ubuntu16_template]]], indirect=True)
def test_migrations_different_os_templates(request, appliance, v2v_providers, host_creds,
                                    conversion_tags,
                                    form_data_multiple_vm_obj_single_datastore,
                                    soft_assert):
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    # form_data_multiple_vm_obj_single_datastore has form_data at [0]
    mapping = infrastructure_mapping_collection.create(
        form_data_multiple_vm_obj_single_datastore[0])

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    # form_data_multiple_vm_obj_single_datastore has list of vm_objects at [1]
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_multiple_vm_obj_single_datastore[1], start_migration=True)
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
    view.items_on_page.item_select('15')
    vms = request_details_list.read()

    wait_for(func=view.plan_in_progress, message="migration plan is in progress, be patient please",
     delay=5, num_sec=3600)

    for vm in vms:
        soft_assert(request_details_list.is_successful(vm) and
         not request_details_list.is_errored(vm))

    rhv_prov = v2v_providers[1]
    collection = rhv_prov.appliance.provider_based_collection(rhv_prov)
    # validate MAC address matches between source and target VMs
    for src_vm in form_data_multiple_vm_obj_single_datastore[1]:
        migrated_vm = collection.instantiate(src_vm.name, rhv_prov)
        soft_assert(src_vm.mac_address == migrated_vm.mac_address)


def test_conversion_host_tags(appliance, v2v_providers):
    """Tests following cases:

    1)Test Attribute in UI indicating host has/has not been configured as conversion host like Tags
    2)Test converstion host tags
    """
    tag1 = (appliance.collections.categories.instantiate(
            display_name='V2V - Transformation Host *')
            .collections.tags.instantiate(display_name='t'))

    tag2 = (appliance.collections.categories.instantiate(
            display_name='V2V - Transformation Method')
            .collections.tags.instantiate(display_name='VDDK'))

    host = v2v_providers[1].hosts.all()[0]
    # Remove any prior tags
    host.remove_tags(host.get_tags())

    host.add_tag(tag1)
    assert host.get_tags()[0].category.display_name in tag1.category.display_name
    host.remove_tag(tag1)

    host.add_tag(tag2)
    assert host.get_tags()[0].category.display_name in tag2.category.display_name
    host.remove_tag(tag2)

    host.remove_tags(host.get_tags())


@pytest.mark.parametrize('conversion_tags, form_data_vm_obj_single_datastore', [['SSH',
    ['nfs', 'nfs', rhel7_minimal]]], indirect=True)
def test_single_vm_migration_with_ssh(request, appliance, v2v_providers, host_creds,
                                    conversion_tags,
                                    form_data_vm_obj_single_datastore):
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    # form_data_vm_obj_single_datastore has form_data at [0]
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore[0])

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    # form_data_vm_obj_single_datastore has list of vm_obj at [0]
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore[1], start_migration=True)

    # explicit wait for spinner of in-progress status card
    view = appliance.browser.create_view(navigator.get_class(migration_plan_collection, 'All').VIEW)
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=5, num_sec=150,
        handle_exception=True)

    # wait until plan is in progress
    wait_for(func=view.plan_in_progress, func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=5, num_sec=1800)

    view.migr_dropdown.item_select("Completed Plans")
    view.wait_displayed()
    logger.info("For plan %s, migration status after completion: %s, total time elapsed: %s",
        migration_plan.name,
        view.migration_plans_completed_list.get_vm_count_in_plan(migration_plan.name),
        view.migration_plans_completed_list.get_clock(migration_plan.name))
    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan.name)


@pytest.mark.parametrize('form_data_vm_obj_single_datastore', [['nfs', 'nfs', rhel7_minimal]],
    indirect=True)
@pytest.mark.parametrize('power_state', ['RUNNING', 'STOPPED'])
def test_single_vm_migration_power_state_tags_retirement(request, appliance, v2v_providers,
                                    host_creds, conversion_tags,
                                    form_data_vm_obj_single_datastore,
                                    power_state):
    # Test VM migration power state and tags are preserved
    # form_data_vm_obj_single_datastore has list of vm_obj at [1]
    # as this is single_vm_migration it only has one vm_obj, which we extract on next line
    vm = form_data_vm_obj_single_datastore[1][0]
    if power_state not in vm.mgmt.state:
        if power_state == 'RUNNING':
            vm.mgmt.start()
        elif power_state == 'STOPPED':
            vm.mgmt.stop()
    tag = (appliance.collections.categories.instantiate(display_name='Owner *').collections.tags
        .instantiate(display_name='Production Linux Team'))
    vm.add_tag(tag)
    vm.set_retirement_date(offset={'hours': 1})

    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    # form_data_vm_obj_single_datastore has form_data at [0]
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore[0])

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    # form_data_vm_obj_single_datastore has list of vm_obj at [1]
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore[1], start_migration=True)

    # explicit wait for spinner of in-progress status card
    view = appliance.browser.create_view(navigator.get_class(migration_plan_collection, 'All').VIEW)
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=5, num_sec=150,
        handle_exception=True)

    # wait until plan is in progress
    wait_for(func=view.plan_in_progress, func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=5, num_sec=1800)

    view.migr_dropdown.item_select("Completed Plans")
    view.wait_displayed()
    logger.info("For plan %s, migration status after completion: %s, total time elapsed: %s",
        migration_plan.name,
        view.migration_plans_completed_list.get_vm_count_in_plan(migration_plan.name),
        view.migration_plans_completed_list.get_clock(migration_plan.name))
    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan.name)
    # check power state on migrated VM
    rhv_prov = v2v_providers[1]
    migrated_vm = rhv_prov.mgmt.get_vm((form_data_vm_obj_single_datastore[1][0]).name)
    assert power_state in migrated_vm.state
    # check tags
    vm_obj = appliance.collections.infra_vms.instantiate(migrated_vm.name, rhv_prov)
    owner_tag = None
    for t in vm_obj.get_tags():
        if tag.display_name in t.display_name:
            owner_tag = t
    assert owner_tag is not None and tag.display_name in owner_tag.display_name
    # If Never is not there, that means retirement is set.
    assert 'Never' not in vm_obj.retirement_date


@pytest.mark.parametrize('host_creds, form_data_multiple_vm_obj_single_datastore', [['multi-host',
    ['nfs', 'nfs', [rhel7_minimal, ubuntu16_template, rhel69_template, win7_template]]]],
    indirect=True)
def test_multi_host_multi_vm_migration(request, appliance, v2v_providers, host_creds,
                                    conversion_tags, soft_assert,
                                    form_data_multiple_vm_obj_single_datastore):
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    # form_data_multiple_vm_obj_single_datastore has form_data at [0]
    mapping = infrastructure_mapping_collection.create(
        form_data_multiple_vm_obj_single_datastore[0])

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    # form_data_multiple_vm_obj_single_datastore has list of vm_objs at [1]
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_multiple_vm_obj_single_datastore[1], start_migration=True)
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
    view.items_on_page.item_select('15')
    # testing multi-host utilization

    def _is_migration_started():
        for vm in vms:
            if request_details_list.get_message_text(vm) != 'Migrating':
                return False
        return True

    wait_for(func=_is_migration_started, message="migration is not started for all VMs, "
        "be patient please", delay=5, num_sec=300)

    hosts_dict = {key.name: [] for key in host_creds}
    for vm in vms:
        popup_text = request_details_list.read_additional_info_popup(vm)
        # open__additional_info_popup function also closes opened popup in our case
        request_details_list.open_additional_info_popup(vm)
        if popup_text['Conversion Host'] in hosts_dict:
            hosts_dict[popup_text['Conversion Host']].append(vm)
    for host in hosts_dict:
        logger.info("Host: {} is migrating VMs: {}".format(host, hosts_dict[host]))
        assert len(hosts_dict[host]) > 0, ("Conversion Host: {} not being utilized for migration!"
            .format(host))

    wait_for(func=view.plan_in_progress, message="migration plan is in progress, be patient please",
     delay=5, num_sec=14400)

    for vm in vms:
        soft_assert(request_details_list.is_successful(vm) and
         not request_details_list.is_errored(vm))
