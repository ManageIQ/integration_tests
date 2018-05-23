import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.markers.env_markers.provider import ONE_PER_CATEGORY
from cfme.networks.provider import NetworkProvider
from cfme.networks.views import (CloudNetworkView, SubnetView, NetworkRouterView, SecurityGroupView,
                                 NetworkPortView, BalancerView, FloatingIpView)
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.usefixtures('setup_provider')
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
@pytest.mark.provider([OpenStackProvider], selector=ONE_PER_CATEGORY)
@pytest.mark.tier(2)
def test_tagvis_network_provider_children(provider, appliance, request, relationship, view,
                                          tag, user_restricted):
    """
    Polarion:
        assignee: rbabyuk
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    prov_view = navigate_to(provider, 'Details')
    net_prov_name = prov_view.entities.summary("Relationships").get_text_of("Network Manager")
    collection = appliance.collections.network_providers
    network_provider = collection.instantiate(prov_class=NetworkProvider, name=net_prov_name)
    network_provider.add_tag(tag=tag)

    request.addfinalizer(lambda: network_provider.remove_tag(tag=tag))

    actual_visibility = child_visibility(appliance, network_provider, relationship, view)
    assert actual_visibility

    with user_restricted:
        actual_visibility = child_visibility(appliance, network_provider, relationship, view)
        assert not actual_visibility
