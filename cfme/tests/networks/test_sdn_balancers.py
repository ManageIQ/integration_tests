import pytest
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([AzureProvider, EC2Provider, OpenStackProvider],
                         scope='module')
]


def test_prov_balances_number(appliance):
    """
    Test number of balancers on 1 provider
    Prerequisites:
        Only one refreshed cloud provider in cfme database
    """
    prov_collection = appliance.collections.network_providers
    providers = prov_collection.all()
    for prov in providers:
        view = navigate_to(prov, 'Details')
        balancers_number = view.entities.relationships.get_text_of('Load Balancers')
        sum_all = len(prov.balancers.all())
        assert int(balancers_number) == sum_all


def test_balances_detail(provider, appliance):
    """ Test of getting attribute from balancer object """
    collection = appliance.collections.network_providers
    providers = collection.all()
    for prov in providers:
        for balancer in prov.balancers.all():
            check = balancer.health_checks
            assert check is not None

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
