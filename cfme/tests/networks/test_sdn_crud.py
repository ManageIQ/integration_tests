import pytest
from utils import testgen
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from utils.appliance.implementations.ui import navigate_to
import cfme.fixtures.pytest_selenium as sel

from cfme.web_ui import Region
from cfme.networks.provider import NetworkProvider
from cfme.networks.cloud_network import CloudNetwork

pytest_generate_tests = testgen.generate(classes=[EC2Provider, OpenStackProvider, AzureProvider], scope = 'module')
pytestmark = pytest.mark.usefixtures('setup_provider')

details_page = Region(infoblock_type='detail')

#Alternative to bugged command
#provider_view.contents.relationships.click_at("Network Manager")
def click_relationship(network_provider, sub_name):
    ''' Click on relationship name, if possible '''
    value = network_provider.get_detail("Relationships", sub_name)
    if value != "0":
        sel.click(details_page.infoblock.element("Relationships", sub_name))

@pytest.mark.tier(1)
def test_sdn_crud(provider, appliance):
    ''' Test for functional addition of network manager with cloud provider
        and functional references on detail page
    Prerequisites: Cloud provider in cfme
    '''

    net_prov_name = provider.get_detail("Relationships", "Network Manager")
    network_provider = NetworkProvider(name=net_prov_name, appliance = appliance)
    parent_name = network_provider.get_detail("Relationships", "Parent Cloud Provider")
    assert parent_name == provider.name

    testing_list = ["Cloud Networks", "Cloud Subnets", "Network Routers", "Security Groups", "Floating IPs", "Network Ports", "Load Balancers"]
    for testing_name in testing_list:
        click_relationship(network_provider, testing_name)

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()

    with pytest.raises(Exception):
        navigate_to(network_provider, "Details")
