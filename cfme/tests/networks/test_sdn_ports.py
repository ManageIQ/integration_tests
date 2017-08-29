import pytest
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.networks.network_port import NetworkPortCollection
from cfme.networks.provider import NetworkProviderCollection
from utils import testgen
from utils.appliance.implementations.ui import navigate_to


pytest_generate_tests = testgen.generate(
    classes=[AzureProvider, EC2Provider, OpenStackProvider], scope='module')
pytestmark = pytest.mark.usefixtures('setup_provider')


def test_port_detail_name(provider):
    ''' Test equality of quadicon and detail names '''
    port_collection = NetworkPortCollection()
    ports = port_collection.all()
    if len(ports) > 5:
        ports = ports[:5]
    for port in ports:
        view = navigate_to(port, 'Details')
        det_name = view.entities.properties.get_text_of('Name')
        assert port.name == det_name


def test_port_net_prov(provider):
    ''' Test functionality of quadicon and detail network providers'''
    prov_collection = NetworkProviderCollection()
    port_collection = prov_collection.ports
    providers = [entity.name for entity in prov_collection.all()]
    ports = port_collection.all()
    if len(ports) > 5:
        ports = ports[:5]
    for port in ports:
        try:
            view = navigate_to(port, 'Details')
            prov_name = view.entities.relationships.get_text_of('Network Manager')
        except Exception:
            continue
        assert prov_name in providers

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
