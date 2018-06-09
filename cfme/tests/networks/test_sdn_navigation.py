import pytest

from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.networks.provider import NetworkProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([EC2Provider, AzureProvider, OpenStackProvider, GCEProvider],
                         scope='function')
]


@pytest.mark.parametrize("tested_part", ["Cloud Subnets", "Cloud Networks", "Network Routers",
                         "Security Groups", "Network Ports", "Load Balancers"])
def test_sdn_provider_relationships_navigation(provider, tested_part, appliance):
    """
    Metadata:
        test_flag: sdn, relationship
    """
    view = navigate_to(provider, 'Details')
    net_prov_name = view.entities.summary("Relationships").get_text_of("Network Manager")

    collection = appliance.collections.network_providers
    network_provider = collection.instantiate(prov_class=NetworkProvider, name=net_prov_name)

    view = navigate_to(network_provider, 'Details')
    value = view.entities.relationships.get_text_of(tested_part)
    if value != "0":
        navigate_to(network_provider, tested_part.replace(' ', ''))


def test_provider_topology_navigation(provider, appliance):
    """
    Metadata:
        test_flag: relationship
    """
    view = navigate_to(provider, 'Details')
    net_prov_name = view.entities.summary("Relationships").get_text_of("Network Manager")

    collection = appliance.collections.network_providers
    network_provider = collection.instantiate(prov_class=NetworkProvider, name=net_prov_name)

    navigate_to(network_provider, "TopologyFromDetails")

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
