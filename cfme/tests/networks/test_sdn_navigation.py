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


def test_provider_relationships_navigation(provider, appliance):
    net_prov_name = provider.get_detail("Relationships", "Network Manager")
    network_provider = NetworkProvider(name=net_prov_name, appliance=appliance)
    tested_parts = ["Cloud Subnets", "Cloud Networks", "Network Routers",
                  "Security Groups", "Floating IPs", "Network Ports", "Load Balancers"]
    final_locations = ["Subnets", "Networks", "Network Routers", "Security Groups",
                     "Floating IPs", "Network Ports", "Load Balancers"]

    for tested_part, final_location in zip(tested_parts, final_locations):
        value = network_provider.get_detail("Relationships", tested_part)
        if value != "0":
            navigate_to(network_provider, tested_part.replace(' ', ''))


def test_provider_topology_navigation(provider, appliance):
    net_prov_name = provider.get_detail("Relationships", "Network Manager")
    network_provider = NetworkProvider(name=net_prov_name, appliance=appliance)
    navigate_to(network_provider, "TopologyFromDetails")

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
