import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.networks.views import NetworkRouterView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update


pytestmark = [
    pytest.mark.provider([OpenStackProvider], scope="module"),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.ignore_stream("5.8")
]


def test_network_router_crud(appliance, provider):
    """Test crud of sdn router."""
    router_collection = appliance.collections.network_routers
    test_name = "test_router_{}".format(fauxfactory.gen_alphanumeric(6))
    net_manager = "{} Network Manager".format(provider.name)
    router = router_collection.create(test_name, provider, "admin", net_manager)
    assert router.exists
    new_test_name = "{}_changed".format(test_name)
    with update(router):
        router.name = new_test_name
    view = navigate_to(router, "Details")
    assert view.title.text == "{} (Summary)".format(new_test_name)
    assert net_manager == view.entities.relationships.get_text_of("Network Manager")
    router.delete()


def test_cancel_adding_router(appliance, provider):
    """Test uncompleted adding router."""
    router_collection = appliance.collections.network_routers
    test_name = "test_router_{}".format(fauxfactory.gen_alphanumeric(6))
    view = navigate_to(router_collection, "Add")
    view.router_name.fill(test_name)
    view.cancel.click()
    view = router_collection.create_view(NetworkRouterView)
    view.flash.assert_success_message("Add of new Network Router was cancelled by the user")


def test_cloud_network_crud(provider, appliance):
    """Test adding cloud network in ui."""
    test_name = "test_network_{}".format(fauxfactory.gen_alphanumeric(6))
    net_manager = "{} Network Manager".format(provider.name)
    collection = appliance.collections.cloud_networks
    network = collection.create(test_name, "admin", provider, net_manager, "Local", is_shared=True)
    assert network.exists
    new_test_name = "{}_changed".format(test_name)
    with update(network):
        network.name = new_test_name
    view = navigate_to(network, "Details")
    assert view.title.text == "{} (Summary)".format(new_test_name)
    assert net_manager == view.entities.relationships.get_text_of("Network Manager")
    network.delete()
    assert not network.exists


@pytest.mark.parametrize("ip_version", [("4", "192.168.23.0/24"),
                                        ("6", "2001:db6::/64")],
                         ids=lambda ip_version: "ipv{}".format(ip_version[0]))
def test_subnet_crud(provider, appliance, ip_version):
    """Test adding subnet in ui."""
    test_name = "test_subnet_{}".format(fauxfactory.gen_alphanumeric(6))
    net_manager = "{} Network Manager".format(provider.name)
    collection = appliance.collections.network_subnets
    subnet = collection.create(test_name, "admin", provider, net_manager, "private", ip_version)
    assert subnet.exists
    new_test_name = "{}_changed".format(test_name)
    with update(subnet):
        subnet.name = new_test_name
    view = navigate_to(subnet, "Details")
    assert view.title == new_test_name
    assert net_manager == view.entities.relationships.get_text_of("Network Manager")
    subnet.delete()
    assert not subnet.exists


@pytest.mark.tier(3)
def test_security_group_crud(appliance, provider):
    """ This will test whether it will create new Security Group and then deletes it.
    Steps:
        * Select Network Manager.
        * Provide Security groups name.
        * Provide Security groups Description.
        * Select Cloud Tenant.
        * Also delete it.
    """
    # TODO: Update need to be done in future.
    collection = appliance.collections.network_security_groups
    sec_group = collection.create(name=fauxfactory.gen_alphanumeric(),
                                  description=fauxfactory.gen_alphanumeric(),
                                  provider=provider,
                                  wait=True)
    assert sec_group.exists
    sec_group.delete(wait=True)
    assert not sec_group.exists


@pytest.mark.tier(3)
def test_security_group_create_cancel(appliance, provider):
    """ This will test cancelling on adding a security groups.

    Steps:
        * Select Network Manager.
        * Provide Security groups name.
        * Provide Security groups Description.
        * Select Cloud Tenant.
        * Cancel it.
    """
    security_group = appliance.collections.network_security_groups
    sec_group = security_group.create(name=fauxfactory.gen_alphanumeric(),
                                      description=fauxfactory.gen_alphanumeric(),
                                      provider=provider,
                                      cancel=True)
    assert not sec_group.exists
