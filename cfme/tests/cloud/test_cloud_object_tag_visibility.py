import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.availability_zone import AvailabilityZone
from cfme.cloud.flavor import Flavor
from cfme.cloud.instance import Instance
from cfme.cloud.instance.image import Image
from cfme.cloud.keypairs import KeyPair
from cfme.cloud.stack import Stack
from cfme.cloud.provider import CloudProvider
from utils import version
from utils.blockers import BZ
from utils.providers import ProviderFilter
from fixtures.provider import setup_one_or_skip

pytestmark = [test_requirements.tag, pytest.mark.tier(2)]


@pytest.fixture(scope='module')
def a_provider(request):
    prov_filter = ProviderFilter(classes=[CloudProvider],
                                 required_fields=[['provisioning', 'stack']])
    return setup_one_or_skip(request, filters=[prov_filter])


test_items = [
    ('providers', CloudProvider),
    ('availability_zones', AvailabilityZone),
    ('flavors', Flavor),
    ('instances', Instance),
    ('templates', Image),
    ('stacks', Stack)
]


@pytest.fixture(params=test_items, ids=[str(test_id[0]) for test_id in test_items],
                scope='module')
def testing_vis_object(request, a_provider, appliance):
    """ Fixture creates class object for tag visibility test
    Returns: class object of certain type
    """
    collection_name, param_class = request.param
    if collection_name == 'stacks':
        return param_class(a_provider.data['provisioning']['stacks'][0], provider=a_provider)
    test_items = getattr(appliance.rest_api.collections, collection_name)
    if not test_items:
        pytest.skip('No content found for test!')
    if collection_name == 'templates':
        item_type = a_provider.data['type']
        for test_item_value in test_items:
            if test_item_value.vendor == item_type:
                return param_class(name=test_item_value.name, provider=a_provider)
    elif collection_name in ['availability_zones', 'flavors', 'instances']:
        return param_class(name=test_items[0].name, provider=a_provider)
    return a_provider


@pytest.yield_fixture(scope="function")
def key_pair(openstack_provider):
    """
    Returns key pair object needed for the test
    """
    keypair = KeyPair(name=fauxfactory.gen_alphanumeric(), provider=openstack_provider)
    keypair.create()
    yield keypair
    keypair.delete(wait=True)


@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_cloud_object(check_item_visibility, testing_vis_object, visibility):
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


@pytest.mark.meta(blockers=[BZ(1441637)])
@pytest.mark.uncollectif(lambda: version.current_version() >= "5.7")
@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_cloud_keypair(check_item_visibility, key_pair, visibility):
    """ Tests infra provider and its items honors tag visibility
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created
        Additionally cloud key_pair should be created

    Steps:
        1. As admin add tag to key_pair
        2. Login as restricted user, key_pair is visible for user
        3. As admin remove tag from key_pair
        4. Login as restricted user, key_pair is not visible for user
    """
    check_item_visibility(key_pair, visibility)
