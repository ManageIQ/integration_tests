"""Tests for Openstack cloud networks, subnets and routers"""

import fauxfactory
import pytest
from selenium.common.exceptions import TimeoutException
from wait_for import TimedOutError

from cfme.cloud.instance.openstack import OpenStackInstance
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.exceptions import ItemNotFound
from cfme.networks.cloud_network import CloudNetwork, CloudNetworkCollection
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.version import current_version
from cfme.utils.wait import wait_for


pytest_generate_tests = testgen.generate([OpenStackProvider],
                                         scope='module')

pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


def delete_entity(entity):
    # TODO: replace this with neutron client request
    try:
        if entity.exists:
            entity.delete()
    except Exception:
        logger.warning('Exception during network entity deletion - skipping..')


def create_network(appliance, provider, is_external):
    collection = appliance.collections.cloud_networks
    network = collection.create(name=fauxfactory.gen_alpha(),
                                tenant=provider.get_yaml_data()['tenant'],
                                provider=provider,
                                network_type='VXLAN',
                                network_manager='{} Network Manager'.format(provider.name),
                                is_external=is_external)
    return network


def create_subnet(appliance, provider, network, cidr):
    collection = appliance.collections.network_subnets
    subnet = collection.create(name=fauxfactory.gen_alpha(),
                               tenant=provider.get_yaml_data()['tenant'],
                               provider=provider,
                               network_manager='{} Network Manager'.format(provider.name),
                               network_name=network.name,
                               cidr=cidr)
    return subnet


def create_router(appliance, provider, ext_gw, ext_network=None, ext_subnet=None):
    collection = appliance.collections.network_routers
    router = collection.create(name=fauxfactory.gen_alpha(),
                               tenant=provider.get_yaml_data()['tenant'],
                               provider=provider,
                               network_manager='{} Network Manager'.format(provider.name),
                               has_external_gw=ext_gw,
                               ext_network=ext_network,
                               ext_network_subnet=ext_subnet)
    return router


@pytest.yield_fixture(scope='function')
def network(provider, appliance):
    """Create cloud network"""
    network = create_network(appliance, provider, is_external=False)
    yield network
    delete_entity(network)


@pytest.yield_fixture(scope='function')
def ext_network(provider, appliance):
    """Create external cloud network"""
    network = create_network(appliance, provider, is_external=True)
    yield network
    delete_entity(network)


@pytest.fixture(scope='module')
def subnet_cidr():
    return '11.11.11.0/24'


@pytest.yield_fixture(scope='function')
def subnet(provider, appliance, network, subnet_cidr):
    """Creates subnet for the given network"""
    subnet = create_subnet(appliance, provider, network, subnet_cidr)
    yield subnet
    delete_entity(subnet)


@pytest.yield_fixture(scope='function')
def ext_subnet(provider, appliance, ext_network, subnet_cidr):
    """Creates subnet for the given external network"""
    subnet = create_subnet(appliance, provider, ext_network, subnet_cidr)
    yield subnet
    delete_entity(subnet)


@pytest.yield_fixture(scope='function')
def router(provider, appliance):
    """Creates network router"""
    router = create_router(appliance, provider, ext_gw=False)
    yield router
    delete_entity(router)


@pytest.yield_fixture(scope='function')
def router_with_gw(provider, appliance, ext_subnet):
    """Creates network router with external network as a gateway"""
    router = create_router(appliance, provider, ext_gw=True, ext_network=ext_subnet.network,
                           ext_subnet=ext_subnet.name)
    yield router
    delete_entity(router)


def test_create_network(network, provider):
    assert network.exists
    assert network.parent_provider.name == provider.name
    assert network.cloud_tenant == provider.get_yaml_data()['tenant']


def test_edit_network(network):
    network.edit(name=fauxfactory.gen_alpha())
    wait_for(network.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=15)
    network.browser.refresh()
    assert network.exists


def test_delete_network(network, appliance):
    network.delete()
    wait_for(network.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=15)
    navigate_to(appliance.collections.cloud_networks, 'All')
    assert not network.exists


def test_create_subnet(subnet, subnet_cidr, provider):
    assert subnet.exists
    assert subnet.parent_provider.name == provider.name
    assert subnet.cloud_tenant == provider.get_yaml_data()['tenant']
    assert subnet.cidr == subnet_cidr
    assert subnet.cloud_network == subnet.network
    assert subnet.net_protocol == 'ipv4'


def test_edit_subnet(subnet):
    subnet.edit(new_name=fauxfactory.gen_alpha())
    wait_for(subnet.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=15)
    subnet.browser.refresh()
    assert subnet.exists


def test_delete_subnet(subnet):
    subnet.delete()
    wait_for(subnet.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=1), timeout=600,
             delay=15)
    subnet.browser.refresh()
    assert not subnet.exists


def test_create_router(router, provider):
    assert router.exists
    assert router.cloud_tenant == provider.get_yaml_data()['tenant']


def test_create_router_with_gateway(router_with_gw, provider):
    assert router_with_gw.exists
    assert router_with_gw.cloud_tenant == provider.get_yaml_data()['tenant']
    assert router_with_gw.cloud_network == router_with_gw.ext_network


def test_edit_router(router):
    router.edit(name=fauxfactory.gen_alpha())
    wait_for(router.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=1), timeout=600,
             delay=15)
    router.browser.refresh()
    assert router.exists


def test_delete_router(router, appliance):
    router.delete()
    wait_for(router.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=1), timeout=600,
             delay=15)
    navigate_to(appliance.collections.network_routers, 'All')
    assert not router.exists
