import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.networks.views import FloatingIpView

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


@pytest.mark.meta(automates=[1652501])
def test_network_ip_address_invalid_address(appliance, provider, network_manager, setup_provider):
    """
    Bugzilla: 1652501
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/10h
    """
    subnets_collection = appliance.collections.network_floating_ips
    invalid_address = 'test'

    with pytest.raises(AssertionError):
        subnets_collection.create(network_manager=network_manager.name,
                                  network_name=provider.data['public_network'],
                                  tenant=provider.data['tenant'], provider=provider,
                                  floating_ip_address=invalid_address)

    view = subnets_collection.create_view(FloatingIpView)
    view.flash.assert_message(
        f"Unable to create Floating IP \"{invalid_address}\": Invalid input for floating_ip_address"
        f". Reason: \'{invalid_address}\' is not a valid IP address.")
