import pytest

from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.exceptions import DestinationNotFound
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([AzureProvider, EC2Provider, GCEProvider], scope='module')
]


@pytest.fixture(scope='module')
def network_prov_with_load_balancers(provider):
    prov_collection = provider.appliance.collections.network_providers
    providers = prov_collection.all()
    available_prov = []
    for prov in providers:
        try:
            sum_all = len(prov.balancers.all())
        except DestinationNotFound:
            continue
        available_prov.append((prov, sum_all))
    return available_prov if available_prov else pytest.skip(
        "No available load balancers for current providers")


def test_sdn_prov_balancers_number(network_prov_with_load_balancers):
    """
    Test number of balancers on 1 provider
    Prerequisites:
        Only one refreshed cloud provider in cfme database
    """
    for prov, sum_all in network_prov_with_load_balancers:
        view = navigate_to(prov, 'Details')
        balancers_number = view.entities.relationships.get_text_of('Load Balancers')
        assert int(balancers_number) == sum_all


@pytest.mark.meta(blockers=[BZ(1544411, forced_streams=['5.8', '5.9'],
                               unblock=lambda provider: not provider.one_of(GCEProvider))])
def test_sdn_balancers_detail(provider, network_prov_with_load_balancers):
    """ Test of getting attribute from balancer object """
    for prov, _ in network_prov_with_load_balancers:
        for balancer in prov.balancers.all():
            check = balancer.health_checks
            assert check is not None
