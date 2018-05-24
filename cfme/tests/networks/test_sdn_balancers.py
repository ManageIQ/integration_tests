import pytest

from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.exceptions import DestinationNotFound
from cfme.utils.appliance.implementations.ui import navigate_to

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


def test_sdn_balancers_detail(provider, network_prov_with_load_balancers):
    """ Test of getting attribute from balancer object """
    for prov, _ in network_prov_with_load_balancers:
        for balancer in prov.balancers.all():
            check = balancer.network_provider
            assert check is not None


# only one provider is needed for that test, used Azure as it has balancers
@pytest.mark.provider([AzureProvider], scope='module', override=True)
@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_sdn_balancers_tagvis(check_item_visibility, visibility, network_prov_with_load_balancers):
    """ Tests network provider and its items honors tag visibility
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag
        2. Login as restricted user, item is visible for user
        3. As admin remove tag
        4. Login as restricted user, item is not visible for user
    """
    balancers_for_provider = network_prov_with_load_balancers[0].balancers.all()
    check_item_visibility(balancers_for_provider[0], visibility)
