import pytest

from cfme.cloud.provider.azure import AzureProvider
from cfme.markers.env_markers.provider import ONE_PER_CATEGORY
from cfme.networks.views import BalancerView
from cfme.networks.views import CloudNetworkView
from cfme.networks.views import FloatingIpView
from cfme.networks.views import NetworkPortView
from cfme.networks.views import NetworkRouterView
from cfme.networks.views import SecurityGroupView
from cfme.networks.views import SubnetView
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([AzureProvider], selector=ONE_PER_CATEGORY, scope='module')
]

network_collections = [
    'network_providers',
    'cloud_networks',
    'network_subnets',
    'network_ports',
    'network_security_groups',
    'network_routers',
    'network_floating_ips'
]

network_test_items = [
    ("Cloud Networks", CloudNetworkView),
    ("Cloud Subnets", SubnetView),
    ("Network Routers", NetworkRouterView),
    ("Security Groups", SecurityGroupView),
    ("Floating IPs", FloatingIpView),
    ("Network Ports", NetworkPortView),
    ("Load Balancers", BalancerView)
]


def child_visibility(appliance, network_provider, relationship, view):
    network_provider_view = navigate_to(network_provider, 'Details')
    if network_provider_view.entities.relationships.get_text_of(relationship) == "0":
        pytest.skip("There are no relationships for {}".format(relationship))
    network_provider_view.entities.relationships.click_at(relationship)
    relationship_view = appliance.browser.create_view(view)
    try:
        if relationship != "Floating IPs":
            assert relationship_view.entities.entity_names
        else:
            assert relationship_view.entities.entity_ids
        actual_visibility = True
    except AssertionError:
        actual_visibility = False

    return actual_visibility


@pytest.mark.parametrize("relationship,view", network_test_items,
                         ids=[rel[0] for rel in network_test_items])
def test_tagvis_network_provider_children(provider, appliance, request, relationship, view,
                                          tag, user_restricted):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/8h
        casecomponent: Tagging
    """
    collection = appliance.collections.network_providers.filter({'provider': provider})
    network_provider = collection.all()[0]

    network_provider.add_tag(tag=tag)
    request.addfinalizer(lambda: network_provider.remove_tag(tag=tag))

    actual_visibility = child_visibility(appliance, network_provider, relationship, view)
    assert actual_visibility

    with user_restricted:
        actual_visibility = child_visibility(appliance, network_provider, relationship, view)
        assert not actual_visibility


@pytest.fixture(params=network_collections, scope='module')
def entity(request, appliance):
    collection_name = request.param
    item_collection = getattr(appliance.collections, collection_name)
    items = item_collection.all()
    if items:
        return items[0]
    else:
        pytest.skip("No content found for test")


@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_network_tagvis(check_item_visibility, entity, visibility):
    """ Tests network provider and its items honors tag visibility
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag
        2. Login as restricted user, item is visible for user
        3. As admin remove tag
        4. Login as restricted user, iten is not visible for user

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Tagging
    """
    check_item_visibility(entity, visibility)
