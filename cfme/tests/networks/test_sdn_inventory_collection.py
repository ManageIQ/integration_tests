import pytest
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.networks.cloud_network import CloudNetwork
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to


pytest_generate_tests = testgen.generate(
    classes=[EC2Provider, AzureProvider, OpenStackProvider], scope='module')
pytestmark = pytest.mark.usefixtures('setup_provider')


@pytest.mark.tier(1)
@pytest.mark.uncollect
def test_sdn_inventory_subnets(provider):
    """ Test to compare mgmt system and ui list of networks
    Note: Those providers don't have list_network() method implemented yet
    """
    network_names = provider.mgmt.list_network()
    for network_name in network_names:
        temp_network = CloudNetwork(name=network_name)
        view = navigate_to(temp_network, 'Details')
        net_name = view.entities.properties.get_text_of('Name')
        assert net_name == network_name

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
