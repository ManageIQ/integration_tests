import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.networks.views import SubnetView

pytestmark = [
    test_requirements.sdn,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([OpenStackProvider], scope="module")
]


@pytest.fixture()
def network_manager(appliance, provider):
    try:
        network_manager, = appliance.collections.network_providers.filter(
            {"provider": provider}).all()
    except ValueError:
        pytest.skip("No network manager found in collections!")
    yield network_manager


@pytest.mark.meta(automates=[1652515])
def test_network_subnet_invalid_cidr(appliance, provider, network_manager, setup_provider):
    """
    Bugzilla: 1652515
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/10h
    """
    subnets_collection = appliance.collections.network_subnets
    invalid_cidr = 'test'

    with pytest.raises(AssertionError):
        subnets_collection.create(network_manager=network_manager.name,
                                  network_name=provider.data['public_network'],
                                  tenant=provider.data['tenant'], cidr=invalid_cidr,
                                  name='test_subnet', provider=provider)

    view = subnets_collection.create_view(SubnetView)
    view.flash.assert_message(
        f"Unable to create Cloud Subnet: Invalid input for cidr. Reason: '{invalid_cidr}' is not a"
        " valid IP subnet.")
