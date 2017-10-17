"""Tests for Openstack cloud networks, subnets and routers"""

import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


pytest_generate_tests = testgen.generate([OpenStackProvider],
                                         scope='module')

pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


SUBNET_CIDR = '11.11.11.0/24'


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
                                tenant=provider.data['provisioning']['cloud_tenant'],
                                provider=provider,
                                network_type='VXLAN',
                                network_manager='{} Network Manager'.format(provider.name),
                                is_external=is_external)
    return network


def create_subnet(appliance, provider, network):
    collection = appliance.collections.network_subnets
    subnet = collection.create(name=fauxfactory.gen_alpha(),
                               tenant=provider.data['provisioning']['cloud_tenant'],
                               provider=provider,
                               network_manager='{} Network Manager'.format(provider.name),
                               network_name=network.name,
                               cidr=SUBNET_CIDR)
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


@pytest.yield_fixture(scope='function')
def subnet(provider, appliance, network):
    """Creates subnet for the given network"""
    subnet = create_subnet(appliance, provider, network)
    yield subnet
    delete_entity(subnet)


@pytest.yield_fixture(scope='function')
def ext_subnet(provider, appliance, ext_network):
    """Creates subnet for the given external network"""
    subnet = create_subnet(appliance, provider, ext_network)
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
    """Creates private cloud network and verifies it's relationships"""
    assert network.exists
    assert network.parent_provider.name == provider.name
    assert network.cloud_tenant == provider.get_yaml_data()['tenant']


def test_edit_network(network):
    """Edits private cloud network's name"""
    network.edit(name=fauxfactory.gen_alpha())
    wait_for(network.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=10)
    network.browser.refresh()
    assert network.exists


def test_delete_network(network):
    """Deletes private cloud network"""
    network.delete()
    wait_for(network.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=10)
    assert not network.exists


def test_create_subnet(subnet, provider):
    """Creates private subnet and verifies it's relationships"""
    assert subnet.exists
    assert subnet.parent_provider.name == provider.name
    assert subnet.cloud_tenant == provider.get_yaml_data()['tenant']
    assert subnet.cidr == SUBNET_CIDR
    assert subnet.cloud_network == subnet.network
    assert subnet.net_protocol == 'ipv4'


def test_edit_subnet(subnet):
    """Edits private subnet's name"""
    subnet.edit(new_name=fauxfactory.gen_alpha())
    wait_for(subnet.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=10)
    assert subnet.exists


def test_delete_subnet(subnet):
    """Deletes private subnet"""
    subnet.delete()
    wait_for(subnet.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=10)
    subnet.browser.refresh()
    assert not subnet.exists


def test_create_router(router, provider):
    """Create router without gateway"""
    assert router.exists
    assert router.cloud_tenant == provider.get_yaml_data()['tenant']


def test_create_router_with_gateway(router_with_gw, provider):
    """Creates router with gateway (external network)"""
    assert router_with_gw.exists
    assert router_with_gw.cloud_tenant == provider.get_yaml_data()['tenant']
    assert router_with_gw.cloud_network == router_with_gw.ext_network


def test_edit_router(router):
    """Edits router's name"""
    router.edit(name=fauxfactory.gen_alpha())
    wait_for(router.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=10)
    router.browser.refresh()
    assert router.exists


def test_delete_router(router, appliance):
    """Deletes router"""
    router.delete()
    wait_for(router.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=10)
    navigate_to(appliance.collections.network_routers, 'All')
    assert not router.exists


def test_clear_router_gateway(router_with_gw):
    """Deletes a gateway from the router"""
    router_with_gw.edit(change_external_gw=False)
    wait_for(router_with_gw.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10),
             timeout=600, delay=10)
    router_with_gw.browser.refresh()
    view = navigate_to(router_with_gw, 'Details')
    assert 'Cloud Network' not in view.entities.relationships.items


def test_add_gateway_to_router(router, ext_subnet):
    """Adds gateway to the router"""
    router.edit(change_external_gw=True, ext_network=ext_subnet.network,
                ext_network_subnet=ext_subnet.name)
    wait_for(router.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=10)
    router.browser.refresh()
    assert router.cloud_network == ext_subnet.network


def test_add_interface_to_router(router, subnet):
    """Adds interface (subnet) to router"""
    router.add_interface(subnet.name)
    wait_for(router.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=10)
    router.browser.refresh()
    # TODO: verify the exact entities' names and relationships, not only count
    view = navigate_to(router, 'Details')
    subnets_count = int(view.entities.relationships.get_text_of('Cloud Subnets'))
    assert subnets_count == 1  # Compare to '1' because clean router was used initially
