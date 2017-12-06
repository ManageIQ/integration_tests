import pytest
import fauxfactory
from widgetastic_patternfly import DropdownItemDisabled

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.networks.cloud_network import CloudNetworkCollection
from cfme.networks.floating_ip import FloatingIPCollection
from cfme.networks.network_router import NetworkRouterCollection
from cfme.networks.security_group import SecurityGroupCollection
from cfme.networks.subnet import SubnetCollection
from cfme.utils import testgen, version
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytest_generate_tests = testgen.generate(classes=[OpenStackProvider], scope='function')
pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
]


@pytest.fixture
def router_collection(appliance):
    return NetworkRouterCollection(appliance)


def test_adding_router(provider, router_collection):
    """ Test crud of sdn router """
    test_name = "test_router_{}".format(fauxfactory.gen_alphanumeric(6))
    net_manager = "{} Network Manager".format(provider.name)

    router = router_collection.create(name=test_name, network_manager=net_manager,
                                      provider=provider, tenant="admin")

    view = navigate_to(router_collection, 'All')
    wait_for(lambda: router_collection.exists(router), delay=50, num_sec=500,
             fail_func=provider.appliance.server.browser.refresh)
    view = navigate_to(router, 'Details')
    assert net_manager == view.entities.relationships.get_text_of("Network Manager")

    view.toolbar.configuration.item_select('Delete this Router', handle_alert=True)
    navigate_to(router_collection, 'All')
    provider.refresh_provider_relationships()
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    wait_for(lambda: not router_collection.exists(router), delay=50, num_sec=500,
             fail_func=provider.appliance.server.browser.refresh)


def test_cancel_adding_router(provider, router_collection):
    """Test uncompleted adding router"""
    test_name = "test_router_{}".format(fauxfactory.gen_alphanumeric(6))

    try:
        view = navigate_to(router_collection, 'Add')
    except DropdownItemDisabled as e:
        raise e("Current provider doen't support adding Network Router")

    view.router_name.fill(test_name)
    view.cancel.click()

    network_router = router_collection.instantiate(name=test_name)
    assert not router_collection.exists(network_router)


@pytest.mark.parametrize("options", [True, False])
def test_adding_cloud_network(provider, appliance, options):
    """Test adding cloud network in ui"""
    test_name = "test_network_{}".format(fauxfactory.gen_alphanumeric(6))
    net_manager = "{} Network Manager".format(provider.name)

    collection = CloudNetworkCollection(appliance)

    if options:
        network = collection.create(name=test_name, provider=provider,
                                    tenant="admin", network_manager=net_manager,
                                    is_external=True, is_shared=True)
    else:
        network = collection.create(name=test_name, provider=provider, tenant="admin",
                                    admin_state=False, network_manager=net_manager)

    navigate_to(collection, 'All')
    wait_for(lambda: collection.exists(network), delay=50, num_sec=500,
             fail_func=provider.appliance.server.browser.refresh)

    view = navigate_to(network, 'Details')
    assert net_manager == view.entities.relationships.get_text_of("Network Manager")
    view.toolbar.configuration.item_select('Delete this Cloud Network', handle_alert=True)

    provider.refresh_provider_relationships()
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    navigate_to(collection, 'All')
    wait_for(lambda: not collection.exists(network), delay=50, num_sec=500,
             fail_func=provider.appliance.server.browser.refresh)


@pytest.mark.parametrize("dhcp", [True, False])
@pytest.mark.parametrize("ip_version", [("4", "192.168.23.0/24"),
                                        ("6", "2001:db6::/64")])
def test_adding_subnet(provider, appliance, dhcp, ip_version):
    """Test adding subnet in ui"""
    test_name = "test_subnet_{}".format(fauxfactory.gen_alphanumeric(6))
    net_manager = "{} Network Manager".format(provider.name)

    collection = SubnetCollection(appliance)
    subnet = collection.create(name=test_name, tenant="admin", network_name=u"nosubnet", dhcp=dhcp,
                               network_manager=net_manager, provider=provider, cidr=ip_version)

    navigate_to(collection, 'All')
    wait_for(lambda: collection.exists(subnet), delay=50, num_sec=500,
             fail_func=provider.appliance.server.browser.refresh)

    view = navigate_to(subnet, 'Details')
    assert net_manager == view.entities.relationships.get_text_of("Network Manager")
    view.toolbar.configuration.item_select('Delete this Cloud Subnet', handle_alert=True)

    provider.refresh_provider_relationships()
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)

    navigate_to(collection, 'All')
    wait_for(lambda: not collection.exists(subnet), delay=50, num_sec=500,
             fail_func=provider.appliance.server.browser.refresh)


def test_adding_security_group(provider, appliance):
    """ Test adding security group in ui"""
    test_name = "test_sec_group_{}".format(fauxfactory.gen_alphanumeric(6))
    description = "test of adding new security group"
    network_manager = "{} Network Manager".format(provider.name)

    collection = SecurityGroupCollection(appliance)
    security_group = collection.create(name=test_name, network_manager=network_manager,
                                       description=description, provider=provider,
                                       tenant="admin")

    navigate_to(collection, 'All')
    wait_for(lambda: collection.exists(security_group), delay=50, num_sec=500,
             fail_func=provider.appliance.server.browser.refresh)

    view = navigate_to(security_group, 'Details')
    assert network_manager == view.entities.relationships.get_text_of("Network Manager")
    view.toolbar.configuration.item_select('Delete this Security Group', handle_alert=True)

    provider.refresh_provider_relationships()
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)

    navigate_to(collection, 'All')
    wait_for(lambda: not collection.exists(security_group), delay=50, num_sec=500,
             fail_func=provider.appliance.server.browser.refresh)


def test_adding_floating_ip(provider, appliance):
    """Test adding floating ip in ui"""
    testing_ip = "10.8.58.190"
    network_manager = "{} Network Manager".format(provider.name)

    collection = FloatingIPCollection(appliance)
    view = navigate_to(collection, 'All')
    view.paginator.set_items_per_page(100)
    current_addresses = [ip.address for ip in collection.all()]

    floating_ip = collection.create(address=testing_ip, tenant="admin",
                                    net_manager=network_manager, provider=provider,
                                    ext_network="public")

    provider.refresh_provider_relationships()
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)

    view = navigate_to(collection, 'All')
    view.paginator.set_items_per_page(100)
    wait_for(lambda: len(collection.all()) > len(current_addresses), delay=50, num_sec=500,
             fail_func=provider.appliance.server.browser.refresh)
    item = [ip for ip in collection.all() if ip.address not in current_addresses]
    assert len(item) == 1
    floating_ip.address = item[0].address

    view = navigate_to(floating_ip, 'Details')
    assert network_manager == view.entities.relationships.get_text_of("Network Manager")
    view.toolbar.configuration.item_select('Delete this Floating IP', handle_alert=True)

    current_addresses = [ip.address for ip in collection.all()]
    provider.refresh_provider_relationships()
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    wait_for(lambda: len(collection.all()) < len(current_addresses), delay=50, num_sec=500,
             fail_func=provider.appliance.server.browser.refresh)
