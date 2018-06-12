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
                         scope='module'),
]


@pytest.mark.tier(1)
def test_sdn_crud(provider, appliance):
    """ Test for functional addition of network manager with cloud provider
        and functional references to components on detail page
    Prerequisites: Cloud provider in cfme

    Metadata:
        test_flag: sdn
    """
    view = navigate_to(provider, 'Details')
    collection = appliance.collections.network_providers.filter({'provider': provider})
    network_provider = random.choice(collection.all())

    view = navigate_to(network_provider, 'Details')
    parent_name = view.entities.relationships.get_text_of("Parent Cloud Provider")

    assert parent_name == provider.name

    testing_list = ["Cloud Networks", "Cloud Subnets", "Network Routers",
                    "Security Groups", "Floating IPs", "Network Ports", "Load Balancers"]
    for testing_name in testing_list:
        view = navigate_to(network_provider, 'Details')
        view.entities.relationships.click_at(testing_name)

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()

    assert not network_provider.exists
