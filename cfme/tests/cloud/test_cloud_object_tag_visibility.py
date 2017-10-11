import pytest

from cfme import test_requirements
from cfme.cloud.availability_zone import AvailabilityZone
from cfme.cloud.flavor import Flavor
from cfme.cloud.instance import Instance
from cfme.cloud.instance.image import Image
from cfme.cloud.keypairs import KeyPairCollection, KeyPair
from cfme.cloud.stack import StackCollection
from cfme.cloud.provider import CloudProvider
from cfme.utils.providers import ProviderFilter
from fixtures.provider import setup_one_or_skip
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.exceptions import ItemNotFound

pytestmark = [test_requirements.tag, pytest.mark.tier(2)]


@pytest.fixture(scope='module')
def a_provider(request):
    prov_filter = ProviderFilter(classes=[CloudProvider],
                                 required_fields=[['provisioning', 'stacks']])
    return setup_one_or_skip(request, filters=[prov_filter])


test_items = [
    ('providers', CloudProvider),
    ('availability_zones', AvailabilityZone),
    ('flavors', Flavor),
    ('instances', Instance),
    ('templates', Image),
    ('stacks', StackCollection),
    ('key_pairs', KeyPairCollection)
]


@pytest.fixture(params=test_items, ids=[str(test_id[0]) for test_id in test_items],
                scope='module')
def testing_vis_object(request, a_provider, appliance):
    """ Fixture creates class object for tag visibility test
    Returns: class object of certain type
    """
    collection_name, param_class = request.param
    if collection_name != 'providers':
        try:
            view = navigate_to(param_class, 'All')
        except AttributeError:
            view = navigate_to(param_class(appliance), 'All')
        try:
            first_entity_name = view.entities.get_first_entity().name
            try:
                return param_class(name=first_entity_name, provider=a_provider)
            except TypeError:
                return param_class(appliance).instantiate(
                    name=first_entity_name, provider=a_provider)
        except ItemNotFound:
            pytest.skip('No content found for test!')
    else:
        return a_provider


# temp check
def remove_tag(vis_object, tag):
    try:
        vis_object.remove_tag(tag=tag)
    except Exception:
        print('Tag is removed')



# @pytest.yield_fixture(scope="function")
# def key_pair(openstack_provider, appliance):
#     """
#     Returns key pair object needed for the test
#     """
#     keypairs = KeyPairCollection(appliance)
#     keypair = keypairs.create(name=fauxfactory.gen_alphanumeric(), provider=openstack_provider)
#     yield keypair
#     keypair.delete(wait=True)

@pytest.mark.uncollectif(lambda: isinstance(testing_vis_object, KeyPair))  # bz 1441637
@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_cloud_object(request, check_item_visibility, testing_vis_object, visibility, tag):
    """ Tests infra provider and its items honors tag visibility
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag
        2. Login as restricted user, item is visible for user
        3. As admin remove tag
        4. Login as restricted user, item is not visible for user
    """
    check_item_visibility(testing_vis_object, visibility)
    request.addfinalizer(lambda: remove_tag(testing_vis_object, tag))


# @pytest.mark.meta(blockers=[BZ(1441637)])
# @pytest.mark.uncollectif(lambda: version.current_version() >= "5.7")
# @pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
# def test_tagvis_cloud_keypair(check_item_visibility, key_pair, visibility):
#     """ Tests infra provider and its items honors tag visibility
#     Prerequisites:
#         Catalog, tag, role, group and restricted user should be created
#         Additionally cloud key_pair should be created
#
#     Steps:
#         1. As admin add tag to key_pair
#         2. Login as restricted user, key_pair is visible for user
#         3. As admin remove tag from key_pair
#         4. Login as restricted user, key_pair is not visible for user
#     """
#     check_item_visibility(key_pair, visibility)


@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'collection'])
def test_object_add_tag_details(request, testing_vis_object, tag, tag_place):
    testing_vis_object.add_tag(tag=tag, details=tag_place)
    # assert any(current_tag.category.display_name == tag.category.display_name and
    #            current_tag.display_name == tag.display_name
    #            for current_tag in testing_vis_object.get_tags()), (
    #     'Assigned tag was not found on the details page')
    testing_vis_object.remove_tag(tag=tag, details=tag_place)
    # assert not (current_tag.category.display_name == tag.category.display_name and
    #             current_tag.display_name == tag.display_name
    #             for current_tag in testing_vis_object.get_tags()), (
    #     'Assigned tag was not found on the details page')
    request.addfinalizer(lambda: remove_tag(testing_vis_object, tag))

