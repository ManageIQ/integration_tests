# -*- coding: utf-8 -*-
"""This module tests tagging of objects in different locations."""
import pytest

from cfme.cloud.keypairs import KeyPair
from cfme.cloud.provider import CloudProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE_PER_CATEGORY
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.usefixtures('setup_provider')
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
        view = navigate_to(collection, destination)
        names = view.entities.entity_names
        if not names:
            pytest.skip("No content found for test")
        return collection.instantiate(name=names[0], provider=provider)


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
        assert any(
            object_tags.category.display_name == tag.category.display_name and
            object_tags.display_name == tag.display_name for object_tags in tags), (
            "{}: {} not in ({})".format(tag.category.display_name, tag.display_name, str(tags)))

        test_item.remove_tag(tag=tag, details=tag_place)
        request.addfinalizer(lambda: tag_cleanup(test_item, tag))

    return _tagging_check


@pytest.mark.provider([CloudProvider], selector=ONE_PER_CATEGORY)
@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_cloud_objects(tagging_check, cloud_test_item, tag_place):
    """ Test for cloud items tagging action from list and details pages """
    tagging_check(cloud_test_item, tag_place)


@pytest.mark.provider([CloudProvider], selector=ONE_PER_CATEGORY)
@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
@pytest.mark.uncollectif(lambda cloud_test_item: cloud_test_item[0] == 'cloud_keypairs')
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
    """
    check_item_visibility(cloud_test_item, visibility)
    request.addfinalizer(lambda: tag_cleanup(cloud_test_item, tag))


@pytest.mark.provider([InfraProvider], selector=ONE_PER_CATEGORY)
@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_infra_objects(tagging_check, infra_test_item, tag_place):
    """ Test for infrastructure items tagging action from list and details pages """
    tagging_check(infra_test_item, tag_place)


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
    """
    check_item_visibility(infra_test_item, visibility)
    request.addfinalizer(lambda: tag_cleanup(cloud_test_item, tag))
