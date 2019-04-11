"""Test to validate End-to-End migrations- functional testing."""
import fauxfactory
import pytest

from cfme.fixtures.provider import (rhel7_minimal, ubuntu16_template,
 rhel69_template, win7_template)
from cfme.fixtures.v2v import _form_data
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION, ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to, navigator
from cfme.utils.generators import random_vm_name
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


@pytest.mark.parametrize('form_data_vm_obj_single_datastore', [['nfs', 'nfs', rhel7_minimal]],
    indirect=True)
@pytest.mark.parametrize('power_state', ['RUNNING', 'STOPPED'])
def test_single_vm_migration_power_state_tags_retirement(request, appliance, v2v_providers,
                                    host_creds, conversion_tags,
                                    form_data_vm_obj_single_datastore,
                                    power_state):
    """
    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1/2h
        subcomponent: RHV
        upstream: yes
    """
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


@pytest.mark.parametrize('form_data_multiple_vm_obj_single_datastore', [['nfs', 'nfs',
        [rhel7_minimal, ubuntu16_template, rhel69_template, win7_template]]], indirect=True)
def test_multi_host_multi_vm_migration(request, appliance, v2v_providers, host_creds,
                                    conversion_tags, soft_assert,
                                    form_data_multiple_vm_obj_single_datastore):
    """
    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1h
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
       characters, such as '@#$(&#@('.

    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1/2h
        subcomponent: RHV
        upstream: yes
    """
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
    src_vm = form_data_vm_obj_single_datastore.vm_list[0]
    migrated_vm = get_migrated_vm_obj(src_vm, v2v_providers.rhv_provider)
    assert src_vm.mac_address == migrated_vm.mac_address


def test_migration_long_name(request, appliance, v2v_providers, host_creds, conversion_tags):
    """Test to check VM name with 64 character should work

    Polarion:
        assignee: sshveta
        initialEstimate: 1h
    """
    source_datastores_list = v2v_providers.vmware_provider.data.get("datastores", [])
    source_datastore = [d.name for d in source_datastores_list if d.type == "nfs"][0]
    collection = appliance.provider_based_collection(v2v_providers.vmware_provider)

    # Following code will create vm name with 64 characters
    vm_name = "{vm_name}{extra_words}".format(vm_name=random_vm_name(context="v2v"),
                                              extra_words=fauxfactory.gen_alpha(51))
    vm_obj = collection.instantiate(
        name=vm_name,
        provider=v2v_providers.vmware_provider,
        template_name=rhel7_minimal(v2v_providers.vmware_provider)["name"],
    )
    vm_obj.create_on_provider(
        timeout=2400,
        find_in_cfme=True,
        allow_skip="default",
        datastore=source_datastore)
    request.addfinalizer(lambda: vm_obj.cleanup_on_provider())
    form_data = _form_data(v2v_providers.vmware_provider, v2v_providers.rhv_provider)

    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="long_name_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_long_name{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=[vm_obj],
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
        fail_cond=False
    )

    # wait until plan is in progress
    wait_for(
        func=view.plan_in_progress,
        func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=5,
        num_sec=1800,
    )
    view.switch_to("Completed Plans")
    view.wait_displayed()
    migration_plan_collection.find_completed_plan(migration_plan)
    logger.info("For plan {plan_name}, migration status : {count}, total time elapsed: {clock}"
                .format(plan_name=migration_plan.name,
                count=view.migration_plans_completed_list.get_vm_count_in_plan(migration_plan.name),
                clock=view.migration_plans_completed_list.get_clock(migration_plan.name)))

    # validate MAC address matches between source and target VMs
    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan.name)
    migrated_vm = get_migrated_vm_obj(vm_obj, v2v_providers.rhv_provider)
    assert vm_obj.mac_address == migrated_vm.mac_address


@pytest.mark.ignore_stream("5.9")
@pytest.mark.parametrize('form_data_vm_obj_single_datastore', [['nfs', 'nfs', rhel7_minimal]],
 indirect=True)
def test_migration_with_edited_mapping(request, appliance, v2v_providers, edited_form_data,
                                       form_data_vm_obj_single_datastore,
                                       host_creds, conversion_tags, soft_assert):
    """
        Test migration with edited infrastructure mapping.
        Steps:
          * create mapping , edit mapping
          * Migrate vm

        Polarion:
            assignee: sshveta
            caseimportance: medium
            initialEstimate: 1/4h
        """
    _form_data, edited_form_data = edited_form_data
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    # vm_obj is a list, with only 1 VM object, hence [0]
    src_vm_obj = form_data_vm_obj_single_datastore.vm_list[0]

    mapping.update(edited_form_data)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore.vm_list,
        start_migration=True)

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
                migration_plan.name, view.migration_plans_completed_list.
                get_vm_count_in_plan(migration_plan.name),
                view.migration_plans_completed_list.get_clock(migration_plan.name))
    # validate MAC address matches between source and target VMs
    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan.name)
    migrated_vm = get_migrated_vm_obj(src_vm_obj, v2v_providers.rhv_provider)
    assert src_vm_obj.mac_address == migrated_vm.mac_address


@pytest.mark.tier(3)
@pytest.mark.ignore_stream('5.9')
@pytest.mark.parametrize('form_data_multiple_vm_obj_single_datastore',
                         [['nfs', 'nfs', [rhel7_minimal, rhel7_minimal]]], indirect=True)
def test_concurrent_migrations(request, appliance, v2v_providers, host_creds, conversion_tags,
                               form_data_multiple_vm_obj_single_datastore):
    """
    Test concurrent migrations with two vms on single conversion host

    Polarion:
        assignee: ytale
        casecomponent: V2V
        subcomponent: RHV
        caseimportance: medium
        initialEstimate: 1/8h
        tags: V2V
    """
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(
        form_data_multiple_vm_obj_single_datastore.form_data
    )

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan1 = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=[form_data_multiple_vm_obj_single_datastore.vm_list[0]],
        start_migration=True
    )

    settings_view = navigate_to(mapping, "MigrationSettings")
    settings_view.max_limit.set_value(3)
    settings_view.apply_btn.click()

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)
        settings_view = navigate_to(mapping, "MigrationSettings")
        settings_view.max_limit.set_value(10)
        settings_view.apply_btn.click()

    migration_plan2 = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=[form_data_multiple_vm_obj_single_datastore.vm_list[1]],
        start_migration=True
    )

    view = navigate_to(migration_plan_collection, 'All')

    def _card_info(plan):
        if view.progress_card.is_plan_started:
            return False
        else:
            card_info = view.progress_card.get_card_info(plan)
            info_msg = "Waiting for an available conversion host"
            assert info_msg in card_info
            return True

    # explicit wait to detect info state from second plan
    wait_for(
        func=_card_info,
        func_args=[migration_plan2.name],
        delay=5,
        num_sec=1800,
        message="migration plan {migration_plan2} is in progress, be patient please".format(
            migration_plan2=migration_plan2.name)
    )

    # wait until first plan is in progress
    wait_for(
        func=view.plan_in_progress,
        func_args=[migration_plan1.name],
        delay=5,
        num_sec=1800,
        message="migration plan {migration_plan1} is in progress, be patient please".format(
            migration_plan1.name)
    )
    view.switch_to("Completed Plans")
    view.wait_displayed()
    migration_plan_collection.find_completed_plan(migration_plan1.name)

    # explicit wait for spinner of second in-progress status card
    view.switch_to("In Progress Plans")
    wait_for(
        func=view.progress_card.is_plan_started,
        func_args=[migration_plan2.name],
        delay=5,
        num_sec=150,
        handle_exception=True,
        fail_cond=False,
        message="migration plan {migration_plan2} is in progress, be patient please".format(
            migration_plan2.name)
    )

    # wait until second plan is in progress
    wait_for(
        func=view.plan_in_progress,
        func_args=[migration_plan2.name],
        delay=5,
        num_sec=1800,
        message="migration plan {migration_plan2} is in progress, be patient please".format(
            migration_plan2.name)
    )
    view.switch_to("Completed Plans")
    view.wait_displayed()
    migration_plan_collection.find_completed_plan(migration_plan2)
    logger.info(
        "For plan %s, migration status after completion: %s, total time elapsed: %s",
        migration_plan2.name,
        view.migration_plans_completed_list.get_vm_count_in_plan(migration_plan2.name),
        view.migration_plans_completed_list.get_clock(migration_plan2.name),
    )
    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan2.name)
