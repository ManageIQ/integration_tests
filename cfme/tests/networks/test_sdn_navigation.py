import pytest
import random

from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
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
        test_flag: sdn
    """
    collection = appliance.collections.network_providers.filter({'provider': provider})
    network_provider = random.choice(collection.all())

    view = navigate_to(network_provider, 'Details')
    value = view.entities.relationships.get_text_of(tested_part)
    if value != "0":
        navigate_to(network_provider, tested_part.replace(' ', ''))


def test_provider_topology_navigation(provider, appliance):
    """
    Metadata:
        test_flag: sdn
    """
    collection = appliance.collections.network_providers.filter({'provider': provider})
    network_provider = random.choice(collection.all())
    view = navigate_to(network_provider, "TopologyFromDetails")
    assert view.is_displayed
