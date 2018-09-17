import pytest
import fauxfactory

from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.wait import wait_for
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([EC2Provider, AzureProvider, OpenStackProvider, GCEProvider],
                         scope='module'),
]


@pytest.mark.rhel_testing
@pytest.mark.tier(1)
def test_sdn_crud(provider, appliance):
    """ Test for functional addition of network manager with cloud provider
        and functional references to components on detail page
    Prerequisites: Cloud provider in cfme

    Metadata:
        test_flag: sdn
    """
    collection = appliance.collections.network_providers.filter({'provider': provider})
    network_provider = collection.all()[0]

    view = navigate_to(network_provider, 'Details')
    parent_name = view.entities.relationships.get_text_of("Parent Cloud Provider")

    assert parent_name == provider.name

    testing_list = ["Cloud Networks", "Cloud Subnets", "Network Routers",
                    "Security Groups", "Floating IPs", "Network Ports", "Load Balancers"]
    for testing_name in testing_list:
        view = navigate_to(network_provider, 'Details')
        view.entities.relationships.click_at(testing_name)

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()

    assert not network_provider.exists


@pytest.mark.ignore_stream('5.9')
@pytest.mark.provider([OpenStackProvider], scope='function', override=True)
def test_router_crud(provider, appliance):
    router_name = 'test_router_crud-{}'.format(fauxfactory.gen_alphanumeric().lower())
    routers = appliance.collections.network_routers
    router = routers.create(name=router_name,
                            provider=provider,
                            tenant=provider.data.networks.cloud_tenant,
                            network_manager=provider.data.networks.network_manager)
    assert router.exists

    router.delete()
    provider.refresh_provider_relationships()

    def router_doesnt_exists():
        # Navigate somewhere else then to Router Details to enforce page refresh.
        collection = appliance.collections.network_providers.filter({'provider': provider})
        return router.name not in (r.name for r in collection.all())

    wait_for(router_doesnt_exists, fail_condition=False, timeout=240, delay=1)
