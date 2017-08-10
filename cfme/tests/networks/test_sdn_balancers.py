import pytest
from utils import testgen
from cfme.cloud.provider.azure import AzureProvider as AP
from cfme.cloud.provider.ec2 import EC2Provider as EP
from cfme.cloud.provider.openstack import OpenStackProvider as OP

from cfme.networks.balancer import Balancer
from cfme.networks.provider import NetworkProvider


pytest_generate_tests = testgen.generate(classes=[AP, EP, OP], scope='module')
pytestmark = pytest.mark.usefixtures('setup_provider')


def test_prov_balances_number(request, provider, appliance):
    '''
    Test number of balancers on 1 provider
    Prerequisites:
        Only one refreshed cloud provider in cfme database
    '''
    sum_all = len(Balancer.get_all())
    sum_manual = 0
    providers = NetworkProvider.get_all()
    for provider in providers:
        prov = NetworkProvider(name=provider)
        balancers_number = prov.get_detail('Relationships', 'Load Balancers')
        sum_manual += int(balancers_number)
    assert sum_manual == sum_all


def test_balances_detail(provider, appliance):
    ''' Test of getting attribute from balancer object '''
    objects = Balancer.get_all()
    for name in objects:
        temp = Balancer(name=name)
        check = temp.get_health_checks()
        assert check is not None

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
