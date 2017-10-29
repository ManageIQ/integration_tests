import pytest
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.networks.provider import NetworkProviderCollection
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to


pytest_generate_tests = testgen.generate(
    classes=[EC2Provider, AzureProvider, OpenStackProvider], scope='module')
pytestmark = pytest.mark.usefixtures('setup_provider')


@pytest.mark.tier(1)
def test_sdn_crud(provider, appliance):
    """ Test for functional addition of network manager with cloud provider
        and functional references to components on detail page
    Prerequisites: Cloud provider in cfme
    """

    view = navigate_to(provider, 'Details')
    net_prov_name = view.entities.relationships.get_text_of("Network Manager")
    collection = NetworkProviderCollection(appliance)
    network_provider = collection.instantiate(name=net_prov_name)

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
