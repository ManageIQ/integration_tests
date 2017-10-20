import pytest

from cfme import test_requirements
from cfme.common.provider import BaseProvider
from cfme.infrastructure.cluster import ClusterCollection
from cfme.infrastructure.host import HostCollection
from cfme.infrastructure.datastore import DatastoreCollection
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import Vm, Template
from fixtures.provider import setup_one_or_skip
from cfme.utils.providers import ProviderFilter


pytestmark = [test_requirements.tag, pytest.mark.tier(2)]


@pytest.fixture(scope='module')
def a_provider(request):
    BaseProvider.clear_providers()
    prov_filter = ProviderFilter(classes=[InfraProvider])
    return setup_one_or_skip(request, filters=[prov_filter])


test_items = [
    ('providers', InfraProvider),
    ('clusters', ClusterCollection),
    ('hosts', HostCollection),
    ('data_stores', DatastoreCollection),
    ('vms', Vm),
    ('templates', Template)
]


@pytest.fixture(params=test_items, ids=[str(test_id[0]) for test_id in test_items],
                scope='function')
def testing_vis_object(request, a_provider, appliance):
    """ Fixture creates class object for tag visibility test
    Returns: class object of certain type
    """
    collection_name, param_class = request.param
    test_items = getattr(appliance.rest_api.collections, collection_name)

    if not test_items:
        pytest.skip('No content found for test!')

    if collection_name in ['templates', 'vms']:
        item_type = a_provider.data.provisioning.catalog_item_type.lower()
        for test_item_value in test_items:
            if test_item_value.vendor == item_type:
                return param_class(name=test_item_value.name, provider=a_provider)
    elif collection_name != 'providers':
        entity_name = test_items[0].name
        if collection_name == 'clusters':
            entity_name = '{} in Datacenter'.format(test_items[0].name)
        try:
            return param_class(name=entity_name, provider=a_provider)
        except TypeError:
            return param_class(appliance).instantiate(name=entity_name, provider=a_provider)
    else:
        return a_provider


@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_infra_object(testing_vis_object, check_item_visibility, visibility):
    """ Tests infra provider and its items honors tag visibility
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag
        2. Login as restricted user, item is visible for user
        3. As admin remove tag
        4. Login as restricted user, iten is not visible for user
    """
    check_item_visibility(testing_vis_object, visibility)
