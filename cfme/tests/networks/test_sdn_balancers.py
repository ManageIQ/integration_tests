import pytest
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.networks.balancer import BalancerCollection
from cfme.networks.provider import NetworkProviderCollection
from utils import testgen
from utils.appliance.implementations.ui import navigate_to


pytest_generate_tests = testgen.generate(
    classes=[AzureProvider, EC2Provider, OpenStackProvider], scope='module')
pytestmark = pytest.mark.usefixtures('setup_provider')


def test_prov_balances_number(provider):
    '''
    Test number of balancers on 1 provider
    Prerequisites:
        Only one refreshed cloud provider in cfme database
    '''
    prov_collection = NetworkProviderCollection()
    bal_collection = prov_collection.balancers
    sum_all = len(bal_collection.all())
    sum_manual = 0
    providers = prov_collection.all()
    for prov in providers:
        view = navigate_to(prov, 'Details')
        balancers_number = view.entities.relationships.get_text_of('Load Balancers')
        sum_manual += int(balancers_number)
    assert sum_manual == sum_all


def test_balances_detail(provider):
    ''' Test of getting attribute from balancer object '''
    bal_collection = BalancerCollection()
    objects = bal_collection.all()
    for name in objects:
        check = name.health_checks
        assert check is not None

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
