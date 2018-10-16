"""Test to validate basic navigations.Later to be replaced with End-to-End functional testing."""
import fauxfactory
import pytest

from widgetastic.exceptions import NoSuchElementException

from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.tests.services.test_service_rbac import new_user, new_group, new_role
from cfme.v2v.migrations import MigrationPlanRequestDetailsView

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


@pytest.mark.parametrize('form_data_single_datastore', [['nfs', 'nfs']], indirect=True)
def test_infra_mapping_ui_assertions(appliance, v2v_providers, form_data_single_datastore,
                                    soft_assert):
    # TODO: This test case does not support update
    # as update is not a supported feature for mapping.
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_single_datastore)
    view = navigate_to(infrastructure_mapping_collection, 'All')
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
    soft_assert(view.form.general.name_help_text.read() == 'Please enter a unique name')


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
def test_v2v_ui_set2(appliance, v2v_providers, form_data_single_datastore, soft_assert):
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
    # Test plan has unique name
    view = navigate_to(migration_plan_collection, 'Add')
    view.general.infra_map.select_by_visible_text(mapping.name)
    view.general.name.fill(plan_name)
    view.general.description.fill(fauxfactory.gen_string("alphanumeric", length=150))
    # following assertion will fail in 5.9.4 as they have not backported this change to 5.9.4
    soft_assert(view.general.name_help_text.read() == 'Please enter a unique name')

    view = navigate_to(migration_plan_collection, 'All')
    soft_assert(plan_name in view.migration_plans_not_started_list.read())
    soft_assert(view.infra_mapping_list.get_associated_plans(mapping.name) == plan_name)
    soft_assert(view.migration_plans_not_started_list.get_plan_description(plan_name) ==
     plan_description)
    # Test Associated Plans count  correctly Displayed in Map List view
    soft_assert(str(len(vm_selected)) in view.migration_plans_not_started_list.
        get_vm_count_in_plan(plan_name))
    soft_assert(view.infra_mapping_list.get_associated_plans_count(mapping.name) ==
     '1 Associated Plan')
    soft_assert(view.infra_mapping_list.get_associated_plans(mapping.name) == plan_name)
    view.migration_plans_not_started_list.select_plan(plan_name)
    view = appliance.browser.create_view(MigrationPlanRequestDetailsView)
    view.wait_displayed()
    soft_assert(set(view.migration_request_details_list.read()) == set(vm_selected))
    view = navigate_to(infrastructure_mapping_collection, 'All')
    view.migration_plans_not_started_list.migrate_plan(plan_name)


def test_migration_rbac(appliance, new_credential, conversion_tags, host_creds, v2v_providers):
    """Test migration with role-based access control"""
    role = new_role(appliance=appliance,
                    product_features=[(['Everything'], False), (['Everything'], True)])
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

    product_features = [(['Everything'], False), (['Everything'], True)]
    role.update({'product_features': product_features})
    with user:
        view = navigate_to(appliance.server, 'Dashboard', wait_for_view=True)
        nav_tree = view.navigation.nav_item_tree()
        # Checks migration option is enabled in navigation
        assert 'Migration' in nav_tree['Compute'], ('Migration not found in nav tree, '
                                                    'rbac should allow this')
