import pytest

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    test_requirements.sdn,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([EC2Provider, AzureProvider, OpenStackProvider, GCEProvider],
                         scope='function')
]


@pytest.mark.parametrize("tested_part", ["Cloud Subnets", "Cloud Networks", "Network Routers",
                         "Security Groups", "Network Ports", "Load Balancers"])
@pytest.mark.uncollectif(lambda tested_part, appliance:
                         "Load Balancers" in tested_part and appliance.version >= "5.11",
                         reason="Cloud Load Balancers are removed in 5.11, see BZ 1672949")
def test_sdn_provider_relationships_navigation(provider, tested_part, appliance):
    """
    Metadata:
        test_flag: sdn, relationship

    Polarion:
        assignee: mmojzis
        casecomponent: WebUI
        initialEstimate: 1/4h
    """
    collection = appliance.collections.network_providers.filter({'provider': provider})
    network_provider = collection.all()[0]

    view = navigate_to(network_provider, 'Details')
    value = view.entities.relationships.get_text_of(tested_part)
    if value != "0":
        navigate_to(network_provider, tested_part.replace(' ', ''))


def test_provider_topology_navigation(provider, appliance):
    """
    Metadata:
        test_flag: relationship

    Polarion:
        assignee: mmojzis
        casecomponent: WebUI
        initialEstimate: 1/10h
    """
    collection = appliance.collections.network_providers.filter({'provider': provider})
    network_provider = collection.all()[0]
    view = navigate_to(network_provider, "TopologyFromDetails")
    assert view.is_displayed
