import pytest
from utils import testgen
from cfme.cloud.provider.ec2 import EC2Provider as EP
from cfme.cloud.provider.azure import AzureProvider as AP
from cfme.cloud.provider.openstack import OpenStackProvider as OP
from cfme.networks.cloud_network import CloudNetwork


pytest_generate_tests = testgen.generate(classes=[EP, AP, OP], scope = 'module')
pytestmark = pytest.mark.usefixtures('setup_provider')


@pytest.mark.tier(1)
@pytest.mark.uncollectif(
    lambda provider: not provider.one_of(OP))
def test_sdn_inventory_subnets(provider):
    ''' Test to compare mgmt system and ui list of networks
    Note: EC2 and Azure don't have list_network() method implemented yet
    '''
    network_names = provider.mgmt.list_network()
    for network_name in network_names:
        temp_network = CloudNetwork(name=network_name)
        net_name = temp_network.get_detail("Properties","Name")
        assert net_name == network_name

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
