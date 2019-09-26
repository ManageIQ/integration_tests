import pytest

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.exceptions import ItemNotFound
from cfme.exceptions import ManyEntitiesFound
from cfme.networks.network_port import NetworkPortCollection
from cfme.networks.provider import NetworkProviderCollection
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    test_requirements.sdn,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([AzureProvider, EC2Provider, OpenStackProvider, GCEProvider],
                         scope='module')
]


def test_sdn_port_detail_name(provider, appliance):
    """ Test equality of quadicon and detail names

    Metadata:
        test_flag: sdn

    Polarion:
        assignee: mmojzis
        casecomponent: WebUI
        initialEstimate: 1/4h
    """
    port_collection = NetworkPortCollection(appliance)
    ports = port_collection.all()
    if len(ports) > 5:
        ports = ports[:5]
    for port in ports:
        try:
            view = navigate_to(port, 'Details')
            det_name = view.entities.properties.get_text_of('Name')
            assert port.name == det_name
        except ManyEntitiesFound:
            pass


def test_sdn_port_net_prov(provider, appliance):
    """ Test functionality of quadicon and detail network providers

    Metadata:
        test_flag: sdn

    Polarion:
        assignee: mmojzis
        casecomponent: WebUI
        initialEstimate: 1/4h
    """
    prov_collection = NetworkProviderCollection(appliance)

    for net_provider in prov_collection.all():
        for port in net_provider.ports.all():
            try:
                view = navigate_to(port, 'Details')
                prov_name = view.entities.relationships.get_text_of('Network Manager')
                assert prov_name == net_provider.name
            except (ManyEntitiesFound, ItemNotFound):  # BZ
                pass
            except NameError:  # does not contain this information in ui, BZ
                pass

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
