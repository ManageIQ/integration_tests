import fauxfactory
import pytest

from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.networks.cloud_network import CloudNetworkCollection
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([RHEVMProvider], scope='module'),
    pytest.mark.uncollectif(
        lambda provider: (provider.one_of(RHEVMProvider) and provider.version < 4),
        'Must be RHEVM provider version >= 4'
    )
]


@pytest.fixture(scope='class', autouse=True)
def ovn_provider(provider, appliance, request):
    view = navigate_to(provider, 'Details')
    try:
        network_provider_name = view.entities.summary(
            'Relationships').get_text_of(
            'Network Manager')
    except NameError:
        network_provider_name = None

    assert network_provider_name is not None

    collection = appliance.collections.network_providers
    request.cls.network_provider = collection.instantiate(name=network_provider_name)

    yield


def refresh_provider(network_provider):
    view = navigate_to(network_provider, 'Details')
    view.toolbar.configuration.item_select(network_provider.refresh_text, handle_alert=True)


@pytest.mark.tier(2)
@pytest.mark.usefixtures('ovn_provider')
class TestOvirtVirtualNetwork(object):

    def test_crud_ovn_network(self):
        collection = CloudNetworkCollection(self.network_provider)

        network = collection.create(
            name=fauxfactory.gen_alphanumeric(8),
            network_manager=self.network_provider.name,
            tenant='tenant',
            network_type='None',
            provider=self.network_provider
        )

        network.edit(name=network.name + '_edited')
        refresh_provider(self.network_provider)
        wait_for(lambda: network.exists, timeout=200, fail_func=network.browser.refresh)

        assert network.exists

        network.delete()
        refresh_provider(self.network_provider)
        wait_for(lambda: not network.exists, timeout=200, fail_func=network.browser.refresh)

        assert not network.exists
