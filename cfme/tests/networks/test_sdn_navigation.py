import pytest
from utils import testgen
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from utils.appliance.implementations.ui import navigate_to
from cfme.networks.provider import NetworkProvider


pytest_generate_tests = testgen.generate(
    classes=[EC2Provider, AzureProvider, OpenStackProvider], scope='module')
pytestmark = pytest.mark.usefixtures('setup_provider')


@pytest.mark.parametrize("tested_part", ["Cloud Subnets", "Cloud Networks", "Network Routers",
                         "Security Groups", "Floating IPs", "Network Ports", "Load Balancers"])
def test_provider_relationships_navigation(provider, tested_part):
    view = navigate_to(provider, 'Details')
    net_prov_name = view.contents.relationships.get_text_of('Network Manager')

    network_provider = NetworkProvider(name=net_prov_name)

    view = navigate_to(network_provider, 'Details')
    value = view.contents.relationships.get_text_of(tested_part)
    if value != "0":
        tested_view = navigate_to(network_provider, tested_part.replace(' ', ''))
        assert tested_view.is_displayed


def test_provider_topology_navigation(provider):
    view = navigate_to(provider, 'Details')
    net_prov_name = view.contents.relationships.get_text_of('Network Manager')
    network_provider = NetworkProvider(name=net_prov_name)
    navigate_to(network_provider, "TopologyFromDetails")

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
