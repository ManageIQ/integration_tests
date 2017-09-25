import pytest

from cfme import test_requirements
from cfme.infrastructure.cluster import ClusterCollection
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import Vm, Template
from fixtures.provider import setup_one_or_skip
from cfme.utils.providers import ProviderFilter
from cfme.utils.update import update


pytestmark = [test_requirements.tag, pytest.mark.tier(2)]

test_items = [
    ('clusters', ClusterCollection),
    ('vms', Vm),
    ('templates', Template)
]


@pytest.fixture(scope='module')
def a_provider(request):
    prov_filter = ProviderFilter(classes=[InfraProvider],
                                 required_fields=['datacenters', 'clusters'])
    return setup_one_or_skip(request, filters=[prov_filter])


@pytest.fixture(params=test_items, ids=[collection_type for collection_type, __ in test_items],
                scope='function')
def testing_vis_object(request, a_provider, appliance):
    """ Fixture creates class object for tag visibility test

    Returns: class object of certain type
    """
    collection_name, param_class = request.param
    collection_rest = getattr(appliance.rest_api.collections, collection_name)

    if not test_items:
        pytest.skip('No content found for test!')

    if collection_name in ['templates', 'vms']:
        item_type = a_provider.data['provisioning']['catalog_item_type'].lower()
        for resource in collection_rest:
            if resource.vendor == item_type:
                return param_class(name=resource.name, provider=a_provider)
    else:
        return param_class(appliance).instantiate(
            name='{} in Datacenter'.format(collection_rest[0].name), provider=a_provider)


@pytest.fixture(scope='module')
def group_tag_datacenter_combination(group_with_tag, a_provider):
    with update(group_with_tag):
        group_with_tag.host_cluster = [a_provider.data['name'], a_provider.data['datacenters'][0]]


@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'not_visible'])
def test_tagvis_tag_datacenter_combination(testing_vis_object, group_tag_datacenter_combination,
                                check_item_visibility, visibility):
    """ Tests template visibility with combination  of tag and selected

        datacenter filters in the group
        Prerequisites:
            Catalog, tag, role, group and restricted user should be created

        Steps:
            1. As admin add tag
            2. Login as restricted user, item is visible for user
            3. As admin remove tag
            4. Login as restricted user, iten is not visible for user
    """
    check_item_visibility(testing_vis_object, visibility)
