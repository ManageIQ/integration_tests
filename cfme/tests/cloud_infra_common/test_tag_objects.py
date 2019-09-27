# -*- coding: utf-8 -*-
"""This module tests tagging of objects in different locations."""
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE
from cfme.markers.env_markers.provider import ONE_PER_CATEGORY
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.usefixtures('setup_provider'),
    test_requirements.tag
]


# tuples of (collection_name, destination)
# get_collection_entity below processes these to navigate and find an entity
# so use (collection_name, None, None) if the thing being tested uses BaseEntity/BaseCollection
# Once everything is converted these should be flattened to just collection names list

infra_test_items = [
    ('infra_provider', 'All'),  # no param_class needed, provider returned directly
    ('infra_vms', 'AllForProvider'),
    ('infra_templates', 'AllForProvider'),
    ('hosts', 'All'),
    ('clusters', 'All'),
    ('datastores', 'All')
]
cloud_test_items = [
    ('cloud_provider', 'All'),  # no param_class needed, provider returned directly
    ('cloud_instances', 'AllForProvider'),
    ('cloud_flavors', 'All'),
    ('cloud_av_zones', 'All'),
    ('cloud_tenants', 'All'),
    ('cloud_keypairs', 'All'),
    ('cloud_images', 'AllForProvider')
]


def get_collection_entity(appliance, collection_name, destination, provider):
    if collection_name in ['infra_provider', 'cloud_provider']:
        return provider
    else:
        collection = getattr(appliance.collections, collection_name)
        collection.filters = {'provider': provider}
        try:
            return collection.all()[0]
        except IndexError:
            pytest.skip("No content found for test")


def tag_cleanup(test_item, tag):
    tags = test_item.get_tags()
    if tags:
        result = (
            not object_tags.category.display_name == tag.category.display_name and
            not object_tags.display_name == tag.display_name for object_tags in tags
        )
        if not result:
            test_item.remove_tag(tag=tag)


@pytest.fixture(params=cloud_test_items, ids=([item[0] for item in cloud_test_items]))
def cloud_test_item(request, appliance, provider):
    collection_name, destination = request.param
    return get_collection_entity(
        appliance, collection_name, destination, provider)


@pytest.fixture(params=infra_test_items, ids=([item[0] for item in infra_test_items]))
def infra_test_item(request, appliance, provider):
    collection_name, destination = request.param
    return get_collection_entity(
        appliance, collection_name, destination, provider)


@pytest.fixture
def tagging_check(tag, request):

    def _tagging_check(test_item, tag_place):
        """ Check if tagging is working
            1. Add tag
            2. Check assigned tag on details page
            3. Remove tag
            4. Check tag unassigned on details page
        """
        test_item.add_tag(tag=tag, details=tag_place)
        tags = test_item.get_tags()
        assert tag in tags, (
            "{}: {} not in ({})".format(tag.category.display_name, tag.display_name, tags))

        test_item.remove_tag(tag=tag, details=tag_place)
        tags = test_item.get_tags()
        assert tag not in tags, (
            "{}: {} in ({})".format(tag.category.display_name, tag.display_name, tags))
        request.addfinalizer(lambda: tag_cleanup(test_item, tag))

    return _tagging_check


@pytest.fixture
def tag_vm(provider, appliance):
    """Get a random vm to tag"""
    view = navigate_to(provider, 'ProviderVms')
    all_names = view.entities.all_entity_names
    return appliance.collections.infra_vms.instantiate(name=all_names[0], provider=provider)


@pytest.fixture
def tag_out_of_10k_values(appliance):
    """Add 10000 values to one of the existing tag category"""
    # Find the name of that category
    result = appliance.ssh_client.run_rails_console("Classification.first.description").output
    category_name = result.split("description")[-1].strip().strip('"')
    # Add 10000 values to that category
    values = appliance.ssh_client.run_rails_console(
        "10000.times { |i| Classification.first.add_entry(:name => i.to_s, :description => i.to_s)}"
    )
    assert values.success
    category = appliance.collections.categories.instantiate(category_name)
    tag = category.collections.tags.instantiate(name="9786", display_name="9786")
    yield tag

    # remove those 10000 values from the appliance
    remove = appliance.ssh_client.run_rails_console(
        "10000.times { |i| Classification.first.entries.last.delete }"
    )
    assert remove.success


@pytest.mark.provider([CloudProvider], selector=ONE_PER_CATEGORY)
@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_cloud_objects(tagging_check, cloud_test_item, tag_place):
    """ Test for cloud items tagging action from list and details pages

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        initialEstimate: 1/12h
    """
    tagging_check(cloud_test_item, tag_place)


@pytest.mark.provider([CloudProvider], selector=ONE_PER_CATEGORY)
@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_cloud_object(check_item_visibility, cloud_test_item, visibility, appliance,
                             request, tag):
    """ Tests infra provider and its items honors tag visibility
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created
    Steps:
        1. As admin add tag
        2. Login as restricted user, item is visible for user
        3. As admin remove tag
        4. Login as restricted user, item is not visible for user

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        initialEstimate: 1/4h
    """
    check_item_visibility(cloud_test_item, visibility)
    request.addfinalizer(lambda: tag_cleanup(cloud_test_item, tag))


@pytest.mark.provider([InfraProvider], selector=ONE_PER_CATEGORY)
@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_infra_objects(tagging_check, infra_test_item, tag_place):
    """ Test for infrastructure items tagging action from list and details pages

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        initialEstimate: 1/12h
    """
    tagging_check(infra_test_item, tag_place)


@pytest.mark.meta(automates=[1726313])
@pytest.mark.provider([InfraProvider], selector=ONE)
def test_tag_vm_10k_category(tag_out_of_10k_values, tag_vm, request):
    """ Test tagging a VM is successful even when a category has 10k values in it

    Bugzilla:
        1726313

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        initialEstimate: 1/6h
    """
    tag_vm.add_tag(tag=tag_out_of_10k_values)
    tags = tag_vm.get_tags()
    request.addfinalizer(lambda: tag_cleanup(tag_vm, tag_out_of_10k_values))
    assert tag_out_of_10k_values in tags


@pytest.mark.provider([InfraProvider], selector=ONE_PER_CATEGORY)
@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_infra_object(infra_test_item, check_item_visibility, visibility, request, tag):
    """ Tests infra provider and its items honors tag visibility
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created
    Steps:
        1. As admin add tag
        2. Login as restricted user, item is visible for user
        3. As admin remove tag
        4. Login as restricted user, iten is not visible for user

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        initialEstimate: 1/12h
    """
    check_item_visibility(infra_test_item, visibility)
    request.addfinalizer(lambda: tag_cleanup(infra_test_item, tag))


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_tag_host_vm_combination():
    """
    Combine My Company tag tab restriction, with Clusters&Host tab and
    VM&templates
    User should be restricted to see tagged host and vm, template

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_config_manager_provider():
    """
    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
        startsin: 5.9
        testSteps:
            1. Add Configuration Manager Provider
            2. Add tag
            3. Check item as restricted user
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_storage_provider_children():
    """
    Providers children should not be visible for
    restricted user

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
        testSteps:
            1. Tag provider
            2. Login as restricted user
            3. Check Providers children visibility
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_cluster_change():
    """
    Enable / Disable a Cluster in the group and check its visibility

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_vm_and_template_modified():
    """
    Enable / Disable a VM's and Template's in the group and check its
    visibility

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_host_change():
    """
    Enable / Disable a host in the group and check its visibility

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_tag_and_cluster_combination():
    """
    Combine My Company tag tab restriction, with Clusters&Host tab
    Visible cluster should match both tab restrictions

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_tag_cluster_vm_combination():
    """
    Combine My Company tag, Cluster and VM/Template
    All restriction should be applied for vm and template

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_cluster_and_vm_combination():
    """
    Combine Host&Cluster with VM&Templates
    Check restricted user can see Cluster and only VMs and Templates from
    this cluster

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_tag_and_host_combination():
    """
    Combine My Company tag tab restriction, with Clusters&Host tab
    Visible host should match both tab restrictions

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_tag_and_vm_combination():
    """
    Combine My Company tag restriction tab with VM&Tepmlates restriction
    tab
    Vm , template should match both tab restrictions

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_ldap_group_host():
    """
    Add LDAP group, assign a host permission and check for the visibility

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_cloud_host_aggregates():
    """
    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
        testSteps:
            1. Create group with tag, use this group for user creation
            2. Add tag(used in group) for cloud host aggregate via detail page
            3. Remove tag for cloud host aggregate via detail page
            4. Add tag for cloud host aggregate via list
            5. Check cloud host aggregate is visible for restricted user
            6. Remove tag for cloud host aggregate via list
            7 . Check cloud host aggregate isn"t visible for restricted user
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_storage_managers():
    """
    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
        testSteps:
            1. Create group with tag, use this group for user creation
            2. Add tag(used in group) for storage manager via detail page
            3. Remove tag for storage manager via detail page
            4. Add tag for storage manager via list
            5. Check storage manager is visible for restricted user
            6. Remove tag for storage manager via list
            7 . Check storage manager isn"t visible for restricted user
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_configuration_management_configured_system():
    """
    Tag a configuration management's configured system and check for its
    visibility

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_group_filter_network_provider():
    """
    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/8h
        testSteps:
            1. Add cloud provider
            2. Create group and select cloud network provider in "Cluster&Hosts"
            filter
            3. Create user assigned to group from step 1
            4. As restricted user, login and navigate to Network Provider
            User should see network provider + all its children
            5.Repeat this case with tag filter
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_infra_networking_switch():
    """
    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: low
        initialEstimate: 1/8h
        testSteps:
            1. Create group with tag, use this group for user creation
            2. Add tag(used in group) for infra networking switch via detail page
            3. Remove tag for infra networking switch via detail page
            4. Add tag for infra networking switch via list
            5. Check infra networking switch is visible for restricted user
            6. Remove tag for infra networking switch via list
            7 . Check infra networking switch isn"t visible for restricted user
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_performance_reports():
    """
    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        caseimportance: medium
        initialEstimate: 1/3h
        testSteps:
            1. Create role with group and user restriction
            2. Create groups with tag
            3. Create user with selected group
            4. Set the group ownership and tag for one of VMs
            5. Generate performance report
            6. As user add widget to dashboard
            7. Check widget content -> User should see only one vm with set
            ownership and tag
    """
    pass
