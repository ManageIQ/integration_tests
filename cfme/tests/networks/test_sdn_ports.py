import pytest
from utils import testgen
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider

from cfme.networks.provider import NetworkProvider
from cfme.networks.network_port import NetworkPort


pytest_generate_tests = testgen.generate(
    classes=[AzureProvider, EC2Provider, OpenStackProvider], scope='module')
pytestmark = pytest.mark.usefixtures('setup_provider')


def test_port_detail_name(request, provider, appliance):
    ''' Test equality of quadicon and detail names '''
    ports = NetworkPort.get_all()
    for port in ports:
        temp_port = NetworkPort(name=port, appliance=appliance)
        det_name = temp_port.get_detail('Properties', 'Name')
        assert port == det_name


def test_port_net_prov(provider, appliance):
    ''' Test functionality of quadicon and detail network providers'''
    providers = NetworkProvider.get_all()
    ports = NetworkPort.get_all()
    for port in ports:
        temp_port = NetworkPort(name=port, appliance=appliance)
        prov = temp_port.get_detail('Relationships', 'Network Manager')
        assert prov in providers

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
