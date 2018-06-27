# -*- coding: utf-8 -*-
"""This module tests tagging of objects in different locations."""
import pytest

from cfme.cloud.keypairs import KeyPair
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([InfraProvider, EC2Provider], scope='module', selector=ONE_PER_TYPE)
]


# tuples of (collection_name, destination)
# get_collection_entity below processes these to navigate and find an entity
# so use (collection_name, None, None) if the thing being tested uses BaseEntity/BaseCollection
# Once everything is converted these should be flattened to just collection names list
cloud_infra_test_items = [
    ('infra_provider', None),  # no param_class needed, provider returned directly
    ('infra_vms', 'ProviderVms'),
    ('infra_templates', 'ProviderTemplates'),
    ('hosts', None),
    ('clusters', None),
    ('datastores', None),
    ('cloud_provider', None),  # no param_class needed, provider returned directly
    ('cloud_instances', 'Instances'),
    ('cloud_flavors', None),
    ('cloud_av_zones', None),
    ('cloud_tenants', None),
    ('cloud_keypairs', None),
    ('cloud_images', 'Images')
]

def get_collection_entity(appliance, collection_name, destination, provider):
    if collection_name in ['infra_provider', 'cloud_provider']:
        return provider
    else:
        collection = getattr(appliance.collections, collection_name)
        view = navigate_to(provider, destination) if destination else navigate_to(collection, 'All')
        names = view.entities.entity_names
        if not names:
            pytest.skip("No content found for test")
        return collection.instantiate(name=names[0], provider=provider)


def _tag_cleanup(test_item, tag):
    tags = test_item.get_tags()
    if tags:
        result = (
            not object_tags.category.display_name == tag.category.display_name and
            not object_tags.display_name == tag.display_name for object_tags in tags
        )
        if not result:
            test_item.remove_tag(tag=tag)
    else:
        result = True
    return result


@pytest.fixture(params=cloud_infra_test_items, ids=([item[0] for item in cloud_infra_test_items]),
                scope='module')
def cloud_infra_test_item(request, appliance, provider):
    collection_name, destination = request.param
    return get_collection_entity(
        appliance, collection_name, destination, provider)


@pytest.fixture(scope='function')
def tagging_check(tag):

    def _tagging_check(test_item, tag_place):
        """ Check if tagging is working
            1. Add tag
            2. Check assigned tag on details page
            3. Remove tag
            4. Check tag unassigned on details page
        """
        _tag_cleanup(test_item, tag)
        test_item.add_tag(tag=tag, details=tag_place)
        tags = test_item.get_tags()
        assert any(
            object_tags.category.display_name == tag.category.display_name and
            object_tags.display_name == tag.display_name for object_tags in tags), (
            "{}: {} not in ({})".format(tag.category.display_name, tag.display_name, str(tags)))

        test_item.remove_tag(tag=tag, details=tag_place)
        assert _tag_cleanup(test_item, tag)

    return _tagging_check


@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_objects(tagging_check, cloud_infra_test_items, tag_place):
    """ Test for cloud items tagging action from list and details pages """
    tagging_check(cloud_infra_test_items, tag_place)


@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_object(check_item_visibility, cloud_infra_test_items, visibility,
                             appliance):
    """ Tests infra provider and its items honors tag visibility
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag
        2. Login as restricted user, item is visible for user
        3. As admin remove tag
        4. Login as restricted user, item is not visible for user
    """
    if isinstance(cloud_infra_test_items, KeyPair) and appliance.version < '5.9':
        pytest.skip('Keypairs visibility works starting 5.9')

        check_item_visibility(cloud_infra_test_items, visibility)
