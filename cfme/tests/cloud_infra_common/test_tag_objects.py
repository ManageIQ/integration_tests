# -*- coding: utf-8 -*-
"""This module tests tagging of objects in different locations."""
import pytest

from cfme.cloud.availability_zone import AvailabilityZone
from cfme.cloud.flavor import Flavor
from cfme.cloud.instance import Instance
from cfme.cloud.instance.image import Image
from cfme.cloud.keypairs import KeyPair
from cfme.cloud.provider import CloudProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import Vm, Template
from fixtures.provider import setup_one_or_skip
from cfme.utils.providers import ProviderFilter
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.tier(2)
]


infra_test_items = [
    ('infra_provider', InfraProvider),
    ('vms', Vm),
    ('templates', Template),
    ('hosts', None),
    ('clusters', None),
    ('datastores', None)
]

cloud_test_items = [
    ('cloud_provider', CloudProvider),
    ('instances', Instance),
    ('flavors', Flavor),
    ('availability_zones', AvailabilityZone),
    ('cloud_tenants', None),
    ('keypairs', None),
    ('templates', Image)
]


@pytest.fixture(scope='module')
def infra_provider(request):
    prov_filter = ProviderFilter(classes=[InfraProvider])
    return setup_one_or_skip(request, filters=[prov_filter])


@pytest.fixture(scope='module')
def cloud_provider(request):
    prov_filter = ProviderFilter(classes=[CloudProvider],
                                 required_fields=[['provisioning', 'stacks']])
    return setup_one_or_skip(request, filters=[prov_filter])


def get_collection_entity(appliance, collection_name, param_class, provider):
    if collection_name in ['infra_provider', 'cloud_provider']:
        return provider
    if not param_class:
        param_class = getattr(appliance.collections, collection_name)
    view = navigate_to(param_class, 'All')
    names = view.entities.entity_names
    if names:
        name = names[0]
    else:
        pytest.skip("No content found for test")
    try:
        return param_class.instantiate(name=name, provider=provider)
    except AttributeError:
        return param_class(name=name, provider=provider)


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


@pytest.fixture(params=cloud_test_items, ids=([item[0] for item in cloud_test_items]),
                scope='module')
def cloud_test_item(request, appliance, cloud_provider):
    collection_name, param_class = request.param
    return get_collection_entity(appliance, collection_name, param_class, cloud_provider)


@pytest.fixture(params=infra_test_items, ids=[item[0] for item in infra_test_items],
                scope='module')
def infra_test_item(request, appliance, infra_provider):
    collection_name, param_class = request.param
    return get_collection_entity(appliance, collection_name, param_class, infra_provider)


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
def test_tag_cloud_objects(tagging_check, cloud_test_item, tag_place):
    """ Test for cloud items tagging action from list and details pages """
    tagging_check(cloud_test_item, tag_place)


@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_infra_objects(tagging_check, infra_test_item, tag_place):
    """ Test for infrastructure items tagging action from list and details pages """
    tagging_check(infra_test_item, tag_place)


@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_cloud_object(check_item_visibility, cloud_test_item, visibility,
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
    if isinstance(cloud_test_item, KeyPair) and appliance.version < '5.9':
        pytest.skip('Keypairs visibility works starting 5.9')

        check_item_visibility(cloud_test_item, visibility)


@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_infra_object(infra_test_item, check_item_visibility,
                             visibility):
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
