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
        handle_exception=True)

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
        handle_exception=True)

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
    assert src_vm.mac_address == migrated_vm.mac_address


@pytest.mark.parametrize('form_data_vm_obj_single_datastore', [['nfs', 'nfs', dual_disk_template]],
                        indirect=True)
def test_dual_disk_vm_migration(request, appliance, v2v_providers, host_creds, conversion_tags,
                                form_data_vm_obj_single_datastore):
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
        handle_exception=True)

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
        handle_exception=True)
    view.progress_card.select_plan(migration_plan.name)
    view = appliance.browser.create_view(navigator.get_class(migration_plan_collection,
                                                             'Details').VIEW)
    view.wait_displayed()
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

    # We just pick the first available host hence [0]
    host = v2v_providers.rhv_provider.hosts.all()[0]
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
        handle_exception=True)

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


@pytest.mark.parametrize('form_data_vm_obj_single_datastore', [['nfs', 'nfs', rhel7_minimal]],
    indirect=True)
@pytest.mark.parametrize('power_state', ['RUNNING', 'STOPPED'])
def test_single_vm_migration_power_state_tags_retirement(request, appliance, v2v_providers,
                                    host_creds, conversion_tags,
                                    form_data_vm_obj_single_datastore,
                                    power_state):
    # Test VM migration power state and tags are preserved
    # as this is single_vm_migration it only has one vm_obj, which we extract on next line
    src_vm = form_data_vm_obj_single_datastore.vm_list[0]
    if power_state not in src_vm.mgmt.state:
        if power_state == 'RUNNING':
            src_vm.mgmt.start()
        elif power_state == 'STOPPED':
            src_vm.mgmt.stop()
    tag = (appliance.collections.categories.instantiate(display_name='Owner *').collections.tags
        .instantiate(display_name='Production Linux Team'))
    src_vm.add_tag(tag)
    src_vm.set_retirement_date(offset={'hours': 1})

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
        handle_exception=True)

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
    # check power state on migrated VM
    rhv_prov = v2v_providers.rhv_provider
    migrated_vm = rhv_prov.mgmt.get_vm(src_vm.name)
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
        "be patient please", delay=5, num_sec=600)

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


@pytest.mark.parametrize('form_data_vm_obj_single_datastore', [['nfs', 'nfs', rhel7_minimal]],
                        indirect=True)
def test_migration_special_char_name(request, appliance, v2v_providers, host_creds, conversion_tags,
                                    form_data_vm_obj_single_datastore):
    """Tests migration where name of migration plan is comprised of special non-alphanumeric
       characters, such as '@#$(&#@('."""
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    # fauxfactory.gen_special() used here to create special character string e.g. #$@#@
    migration_plan = migration_plan_collection.create(
        name="{}".format(fauxfactory.gen_special()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore.vm_list, start_migration=True)

    # explicit wait for spinner of in-progress status card
    view = appliance.browser.create_view(
        navigator.get_class(migration_plan_collection, 'All').VIEW.pick())
    wait_for(func=view.progress_card.is_plan_started, func_args=[migration_plan.name],
        message="migration plan is starting, be patient please", delay=5, num_sec=150,
        handle_exception=True)

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
    src_vm = form_data_vm_obj_single_datastore.vm_list[0]
    migrated_vm = get_migrated_vm_obj(src_vm, v2v_providers.rhv_provider)
    assert src_vm.mac_address == migrated_vm.mac_address
