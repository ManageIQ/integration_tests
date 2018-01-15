import pytest

from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.exceptions import DestinationNotFound
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([AzureProvider, EC2Provider, OpenStackProvider],
                         scope='module')
]


@pytest.fixture(scope='module')
def network_prov_with_load_balancers(appliance):
    prov_collection = appliance.collections.network_providers
    providers = prov_collection.all()
    available_prov = {}
    for prov in providers:
        try:
            sum_all = len(prov.balancers.all())
        except DestinationNotFound:
            pytest.skip("No available load balancers for current provider")
        available_prov[prov] = sum_all
    return available_prov


def test_prov_balances_number(network_prov_with_load_balancers):
    """
    Test number of balancers on 1 provider
    Prerequisites:
        Only one refreshed cloud provider in cfme database
    """
    for prov, sum_all in network_prov_with_load_balancers.items():
        view = navigate_to(prov, 'Details')
        balancers_number = view.entities.relationships.get_text_of('Load Balancers')
        assert int(balancers_number) == sum_all


def test_balances_detail(provider, network_prov_with_load_balancers):
    """ Test of getting attribute from balancer object """
    for prov, _ in network_prov_with_load_balancers.items():
        for balancer in prov.balancers.all():
            check = balancer.health_checks
            assert check is not None

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
