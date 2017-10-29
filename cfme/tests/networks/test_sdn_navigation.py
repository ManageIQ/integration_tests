import pytest
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.networks.provider import NetworkProviderCollection
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to


pytest_generate_tests = testgen.generate(
    classes=[EC2Provider, AzureProvider, OpenStackProvider], scope='function')
pytestmark = pytest.mark.usefixtures('setup_provider')


@pytest.mark.parametrize("tested_part", ["Cloud Subnets", "Cloud Networks", "Network Routers",
                         "Security Groups", "Network Ports", "Load Balancers"])
def test_provider_relationships_navigation(provider, tested_part, appliance):
    view = navigate_to(provider, 'Details')
    net_prov_name = view.entities.relationships.get_text_of('Network Manager')

    collection = NetworkProviderCollection(appliance)
    network_provider = collection.instantiate(name=net_prov_name)

    view = navigate_to(network_provider, 'Details')
    value = view.entities.relationships.get_text_of(tested_part)
    if value != "0":
        navigate_to(network_provider, tested_part.replace(' ', ''))


def test_provider_topology_navigation(provider, appliance):
    view = navigate_to(provider, 'Details')
    net_prov_name = view.entities.relationships.get_text_of('Network Manager')

    collection = NetworkProviderCollection(appliance)
    network_provider = collection.instantiate(name=net_prov_name)

    navigate_to(network_provider, "TopologyFromDetails")

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
