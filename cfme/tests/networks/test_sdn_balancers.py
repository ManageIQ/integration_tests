import pytest
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.networks.provider import NetworkProviderCollection
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to


pytest_generate_tests = testgen.generate(
    classes=[AzureProvider, EC2Provider, OpenStackProvider], scope='module')
pytestmark = pytest.mark.usefixtures('setup_provider')


def test_prov_balances_number(provider, appliance):
    """
    Test number of balancers on 1 provider
    Prerequisites:
        Only one refreshed cloud provider in cfme database
    """
    prov_collection = NetworkProviderCollection(appliance)
    providers = prov_collection.all()
    for prov in providers:
        view = navigate_to(prov, 'Details')
        balancers_number = view.entities.relationships.get_text_of('Load Balancers')
        sum_all = len(prov.balancers.all())
        assert int(balancers_number) == sum_all


def test_balances_detail(provider, appliance):
    """ Test of getting attribute from balancer object """
    collection = NetworkProviderCollection(appliance)
    providers = collection.all()
    for prov in providers:
        for balancer in prov.balancers.all():
            check = balancer.health_checks
            assert check is not None

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
