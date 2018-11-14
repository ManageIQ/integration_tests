"""Test to validate basic navigations.Later to be replaced with End-to-End functional testing."""
import fauxfactory
import pytest

from widgetastic.exceptions import NoSuchElementException

from cfme.exceptions import ItemNotFound
from cfme.fixtures.provider import small_template
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.tests.services.test_service_rbac import new_user, new_group, new_role
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
from cfme.v2v.migrations import MigrationPlanRequestDetailsView


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


@pytest.mark.parametrize('form_data_single_datastore', [['nfs', 'nfs']], indirect=True)
def test_infra_mapping_ui_assertions(appliance, v2v_providers, form_data_single_datastore,
                                    host_creds, conversion_tags, soft_assert):
    # TODO: This test case does not support update
    # as update is not a supported feature for mapping.
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_single_datastore)
    view = navigate_to(infrastructure_mapping_collection, 'All')
    if appliance.version >= '5.10':  # As mapping could be on any page due to pagination
        infrastructure_mapping_collection.find_mapping(mapping)  # We need to find mapping first
    soft_assert(mapping.name in view.infra_mapping_list.read())
    mapping_list = view.infra_mapping_list
    soft_assert(str(mapping_list.get_map_description(mapping.name)) == mapping.description)
    soft_assert(mapping.form_data['cluster']['mappings'][0]['sources'][0].format() in
        mapping_list.get_map_source_clusters(mapping.name)[0])
    soft_assert(mapping.form_data['cluster']['mappings'][0]['target'][0].format() in
     mapping_list.get_map_target_clusters(mapping.name)[0])
    soft_assert(mapping.form_data['datastore'].values()[0]['mappings'][0]['sources'][0].format() in
     mapping_list.get_map_source_datastores(mapping.name)[0])
    soft_assert(mapping.form_data['datastore'].values()[0]['mappings'][0]['target'][0].format() in
     mapping_list.get_map_target_datastores(mapping.name)[0])
    soft_assert(mapping.form_data['network'].values()[0]['mappings'][0]['sources'][0].format() in
     mapping_list.get_map_source_networks(mapping.name)[0])
    soft_assert(mapping.form_data['network'].values()[0]['mappings'][0]['target'][0].format() in
     mapping_list.get_map_target_networks(mapping.name)[0])

    # Testing if refreshing hosts cause any "Network Missing"
    rhv_prov = v2v_providers.rhv_provider
    host = rhv_prov.hosts.all()[0]
    host.refresh(cancel=True)
    view = navigate_to(infrastructure_mapping_collection, 'All', wait_for_view=True)
    mapping_list = view.infra_mapping_list
    soft_assert(mapping_list.get_map_source_networks(mapping.name) != [])
    soft_assert(mapping_list.get_map_target_networks(mapping.name) != [])

    mapping_list.delete_mapping(mapping.name)
    view.browser.refresh()
    view.wait_displayed()
    try:
        assert mapping.name not in view.infra_mapping_list.read()
    except NoSuchElementException:
        # meaning there was only one mapping that is deleted, list is empty
        pass


@pytest.mark.parametrize('form_data_single_datastore', [['nfs', 'nfs']], indirect=True)
def test_v2v_ui_set1(appliance, v2v_providers, form_data_single_datastore, soft_assert):
    """Perform UI Validations on Infra_Mappings Wizard."""
    infrastructure_mapping_collection = appliance.collections.v2v_mappings

    view = navigate_to(infrastructure_mapping_collection, 'Add')
    mapping_name = fauxfactory.gen_string("alphanumeric", length=50)
    view.form.general.name.fill(mapping_name)

    # Assert only 24 characters can be entered in name field
    soft_assert(len(view.form.general.name.read()) == 24)

    mapping_name = fauxfactory.gen_string("alphanumeric", length=10)
    view.form.general.name.fill(mapping_name)
    view.form.general.description.fill(fauxfactory.gen_string("alphanumeric", length=150))

    # Assert only 128 characters can be entered in description field
    soft_assert(len(view.form.general.description.read()) == 128)
    view.form.general.next_btn.click()

    view.form.cluster.wait_displayed()

    # Assert source clusters and target clusters are available
    soft_assert(len(view.form.cluster.source_clusters.all_items) > 0)
    soft_assert(len(view.form.cluster.target_clusters.all_items) > 0)

    # Assert Add Mapping button is disables before selecting source and target clusters
    soft_assert(view.form.cluster.add_mapping.root_browser.
        get_attribute('disabled', view.form.cluster.add_mapping) == 'true')
    view.form.cluster.source_clusters.fill(form_data_single_datastore['cluster']
        ['mappings'][0]['sources'])
    view.form.cluster.target_clusters.fill(form_data_single_datastore['cluster']
        ['mappings'][0]['target'])

    # Test Datacenter name in source and destination mapping select list:
    soft_assert(v2v_providers.vmware_provider.data['datacenters'][0]
                in view.form.cluster.source_clusters.all_items[0])
    soft_assert(v2v_providers.rhv_provider.data['datacenters'][0]
                in view.form.cluster.target_clusters.all_items[0])

    # Assert Add Mapping button is enabled before selecting source and target clusters
    soft_assert(not view.form.cluster.add_mapping.root_browser.
        get_attribute('disabled', view.form.cluster.add_mapping))
    view.form.cluster.add_mapping.click()
    view.form.cluster.next_btn.click()

    # Test multiple Datastore sources can be mapped to single target
    view.form.datastore.wait_displayed()
    datastore_mapping_sources = view.form.datastore.source_datastores.all_items
    datastore_mapping_target = view.form.datastore.target_datastores.all_items[0]
    view.form.datastore.source_datastores.fill(datastore_mapping_sources)
    view.form.datastore.target_datastores.fill([datastore_mapping_target])
    view.form.datastore.add_mapping.click()
    soft_assert(len(view.form.datastore.mappings_tree.mapping_sources) ==
        len(datastore_mapping_sources))

    # next assertion may fail for 5.9.3.3 as we still have size restrictions on datastore mapping
    soft_assert(view.form.datastore.mappings_tree.mapping_targets[0].split('(')[0]
        in datastore_mapping_target)
    view.form.datastore.next_btn.click()

    # Test multiple Network sources can be mapped to single target
    view.form.network.wait_displayed()
    network_mapping_sources = view.form.network.source_networks.all_items
    network_mapping_target = view.form.network.target_networks.all_items[0]
    view.form.network.source_networks.fill(network_mapping_sources)
    view.form.network.target_networks.fill([network_mapping_target])
    view.form.network.add_mapping.click()
    soft_assert(len(view.form.network.mappings_tree.mapping_sources) ==
        len(network_mapping_sources))
    soft_assert(view.form.network.mappings_tree.mapping_targets[0] in network_mapping_target)
    view.form.network.next_btn.click()

    view.form.result.wait_displayed()
    soft_assert(view.form.result.continue_to_plan_wizard.is_displayed)
    view.form.result.close.click()

    # Test multiple mappings cannot be created with same name:
    view = navigate_to(infrastructure_mapping_collection, 'Add')
    view.form.general.name.fill(mapping_name)
    view.form.general.description.fill('some description')
    soft_assert('a unique name' in view.form.general.name_help_text.read())


def test_v2v_ui_no_providers(appliance, v2v_providers, soft_assert):
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    view = navigate_to(infrastructure_mapping_collection, 'All')
    soft_assert(view.create_infrastructure_mapping.is_displayed)
    is_provider_1_deleted = v2v_providers.vmware_provider.delete_if_exists(cancel=False)
    is_provider_2_deleted = v2v_providers.rhv_provider.delete_if_exists(cancel=False)
    # Test after removing Providers, users cannot Create Infrastructure Mapping
    view = navigate_to(infrastructure_mapping_collection, 'All')
    soft_assert(view.configure_providers.is_displayed)
    soft_assert(not view.create_infrastructure_mapping.is_displayed)
    # Test with no provider_setup added migration plans not visible
    # soft_assert(not view.create_migration_plan.is_displayed)
    # Following leaves to appliance in the state it was before this test deleted provider_setup
    if is_provider_1_deleted:
        v2v_providers.vmware_provider.create(validate_inventory=True)
    if is_provider_2_deleted:
        v2v_providers.rhv_provider.create(validate_inventory=True)


@pytest.mark.parametrize('form_data_single_datastore', [['nfs', 'nfs']], indirect=True)
def test_v2v_mapping_with_special_chars(appliance, v2v_providers, form_data_single_datastore,
                                        soft_assert):
    # Test mapping can be created with non-alphanumeric name e.g '!@#$%^&*()_+)=-,./,''[][]]':
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    form_data_single_datastore['general']['name'] = fauxfactory.gen_special(length=10)
    mapping = infrastructure_mapping_collection.create(form_data_single_datastore)
    view = navigate_to(infrastructure_mapping_collection, 'All')
    soft_assert(mapping.name in view.infra_mapping_list.read())
    mapping_list = view.infra_mapping_list
    mapping_list.delete_mapping(mapping.name)
    view.browser.refresh()
    view.wait_displayed()
    try:
        assert mapping.name not in view.infra_mapping_list.read()
    except NoSuchElementException:
        # meaning there was only one mapping that is deleted, list is empty
        pass


@pytest.mark.parametrize('form_data_single_datastore', [['nfs', 'nfs']], indirect=True)
def test_v2v_ui_set2(request, appliance, v2v_providers, form_data_single_datastore, soft_assert):
    # Test migration plan name 24 chars and description 128 chars max length
    # Test earlier infra mapping can be viewed in migration plan wizard
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    migration_plan_collection = appliance.collections.v2v_plans

    mapping = infrastructure_mapping_collection.create(form_data_single_datastore)

    view = navigate_to(migration_plan_collection, 'Add')
    view.general.infra_map.select_by_visible_text(mapping.name)
    soft_assert(view.general.infra_map.read() == mapping.name)

    view.general.name.fill(fauxfactory.gen_string("alphanumeric", length=50))
    # Assert only 24 characters can be entered in name field
    soft_assert(len(view.general.name.read()) == 24)
    plan_name = fauxfactory.gen_string("alphanumeric", length=7)
    view.general.name.fill(plan_name)
    view.general.description.fill(fauxfactory.gen_string("alphanumeric", length=150))
    # Assert only 128 characters can be entered in description field
    soft_assert(len(view.general.description.read()) == 128)
    plan_description = fauxfactory.gen_string("alphanumeric", length=15)
    view.general.description.fill(plan_description)
    view.next_btn.click()
    view.vms.wait_displayed()

    # Test VM Selection based on infrastructure mapping
    # We will have rows in the table if discovery is working
    soft_assert(len([row for row in view.vms.table.rows()]) > 0)

    vm_selected = view.vms.select_by_name('v2v')
    view.next_btn.click()
    view.next_btn.click()
    view.options.wait_displayed()
    view.options.run_migration.select("Save migration plan to run later")
    # Test Create migration plan -Create and Read
    view.options.create.click()
    view.results.close.click()

    @request.addfinalizer
    def _cleanup():
        view = navigate_to(migration_plan_collection, 'All')
        view.migration_plans_not_started_list.migrate_plan(plan_name)

    view = navigate_to(migration_plan_collection, 'All')
    view.wait_displayed()
    soft_assert(plan_name in view.migration_plans_not_started_list.read())
    soft_assert(view.migration_plans_not_started_list.get_plan_description(plan_name) ==
     plan_description)
    # Test Associated Plans count  correctly Displayed in Map List view
    soft_assert(str(len(vm_selected)) in view.migration_plans_not_started_list.
        get_vm_count_in_plan(plan_name))
    view.migration_plans_not_started_list.select_plan(plan_name)
    view = appliance.browser.create_view(MigrationPlanRequestDetailsView)
    view.wait_displayed()
    view.items_on_page.item_select('15')
    soft_assert(set(view.migration_request_details_list.read()) == set(vm_selected))
    # Test plan has unique name
    view = navigate_to(migration_plan_collection, 'All')
    view.create_migration_plan.click()
    view = navigate_to(migration_plan_collection, 'Add')
    view.general.wait_displayed()
    view.general.infra_map.select_by_visible_text(mapping.name)
    view.general.name.fill(plan_name)
    view.general.description.fill(fauxfactory.gen_string("alphanumeric", length=150))
    soft_assert('a unique name' in view.general.name_help_text.read())
    view.cancel_btn.click()

    view = navigate_to(infrastructure_mapping_collection, 'All')
    view.wait_displayed()
    soft_assert(view.infra_mapping_list.get_associated_plans_count(mapping.name) ==
     '1 Associated Plan')
    soft_assert(view.infra_mapping_list.get_associated_plans(mapping.name) == plan_name)


@pytest.mark.parametrize('form_data_multiple_vm_obj_single_datastore', [['nfs', 'nfs',
    [small_template, small_template]]], indirect=True)
def test_v2v_ui_migration_plan_sorting(appliance, v2v_providers, host_creds, conversion_tags,
        form_data_multiple_vm_obj_single_datastore, soft_assert):
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    migration_plan_collection = appliance.collections.v2v_plans

    mapping = infrastructure_mapping_collection.create(
        form_data_multiple_vm_obj_single_datastore[0])

    # creating two plans, with 1 VM in each, hence vm_list[0]/[1]
    plan1 = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=[form_data_multiple_vm_obj_single_datastore.vm_list[0]], start_migration=False)
    plan2 = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()), description="desc_{}"
        .format(fauxfactory.gen_alphanumeric()), infra_map=mapping.name,
        vm_list=[form_data_multiple_vm_obj_single_datastore.vm_list[1]], start_migration=False)

    view = navigate_to(migration_plan_collection, 'All')

    plans_list_before_sort = view.migration_plans_not_started_list.read()
    view.sort_direction.click()
    plans_list_after_sort = view.migration_plans_not_started_list.read()
    soft_assert(plans_list_before_sort != plans_list_after_sort)

    view.migration_plans_not_started_list.schedule_migration(plan1.name, after_mins=5)
    view.wait_displayed()
    view.migration_plans_not_started_list.schedule_migration(plan2.name, after_mins=10)
    view.wait_displayed()
    view.sort_type_dropdown.item_select("Scheduled Time")
    plans_list_before_sort = view.migration_plans_not_started_list.read()
    view.sort_direction.click()
    plans_list_after_sort = view.migration_plans_not_started_list.read()
    soft_assert(plans_list_before_sort != plans_list_after_sort)
    # TODO: Create new method to unschedule the migration plans.
    view.migration_plans_not_started_list.schedule_migration(plan1.name)
    view.wait_displayed()
    view.migration_plans_not_started_list.schedule_migration(plan2.name)

    for plan in (plan1, plan2):
        view.switch_to("Not Started Plans")
        view.wait_displayed()
        try:
            view.migration_plans_not_started_list.migrate_plan(plan.name)
        except ItemNotFound:
            logger.info("Item not found in Not Started List, switching to In Progress plans.")
        view.switch_to("In Progress Plans")
        wait_for(func=view.progress_card.is_plan_started, func_args=[plan.name],
            message="migration plan is starting, be patient please", delay=5, num_sec=150,
            handle_exception=True)
        wait_for(func=view.plan_in_progress, func_args=[plan.name], delay=5, num_sec=600,
            handle_exception=True)

    view.switch_to("Completed Plans")
    view.wait_displayed()
    plans_list_before_sort = view.migration_plans_completed_list.read()
    view.sort_direction.click()
    plans_list_after_sort = view.migration_plans_completed_list.read()
    soft_assert(plans_list_before_sort != plans_list_after_sort)
    # Test Archive completed migration  plan
    view.browser.refresh()
    view.wait_displayed()
    view.switch_to("Completed Plans")
    view.wait_displayed()
    view.migration_plans_completed_list.archive_plan(plan1.name)
    view.switch_to("Archived Plans")
    view.wait_displayed()
    soft_assert(plan1.name in view.migration_plans_archived_list.read())


def test_migration_rbac(appliance, new_credential, v2v_providers):
    """Test migration with role-based access control"""
    role = new_role(appliance=appliance,
                    product_features=[(['Everything'], True)])
    group = new_group(appliance=appliance, role=role.name)
    user = new_user(appliance=appliance, group=group, credential=new_credential)

    product_features = [(['Everything', 'Compute', 'Migration'], False)]
    role.update({'product_features': product_features})
    with user:
        view = navigate_to(appliance.server, 'Dashboard')
        nav_tree = view.navigation.nav_item_tree()
        # Checks migration option is disabled in navigation
        assert 'Migration' not in nav_tree['Compute'], ('Migration found in nav tree, '
                                                        'rbac should not allow this')

    product_features = [(['Everything'], True)]
    role.update({'product_features': product_features})
    with user:
        view = navigate_to(appliance.server, 'Dashboard', wait_for_view=15)
        nav_tree = view.navigation.nav_item_tree()
        # Checks migration option is enabled in navigation
        assert 'Migration' in nav_tree['Compute'], ('Migration not found in nav tree, '
                                                    'rbac should allow this')
