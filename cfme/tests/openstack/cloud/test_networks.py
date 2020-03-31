"""Tests for Openstack cloud networks, subnets and routers"""
import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([OpenStackProvider], scope='module'),
]


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
    network = collection.create(name=fauxfactory.gen_alpha(start="nwk_"),
                                tenant=provider.data.get('provisioning').get('cloud_tenant'),
                                provider=provider,
                                network_type='VXLAN',
                                network_manager=f'{provider.name} Network Manager',
                                is_external=is_external)
    return network


def create_subnet(appliance, provider, network):
    collection = appliance.collections.network_subnets
    subnet = collection.create(name=fauxfactory.gen_alpha(12, start="subnet_"),
                               tenant=provider.data.get('provisioning').get('cloud_tenant'),
                               provider=provider,
                               network_manager=f'{provider.name} Network Manager',
                               network_name=network.name,
                               cidr=SUBNET_CIDR)
    return subnet


def create_router(appliance, provider, ext_gw, ext_network=None, ext_subnet=None):
    collection = appliance.collections.network_routers
    router = collection.create(name=fauxfactory.gen_alpha(12, start="router_"),
                               tenant=provider.data.get('provisioning').get('cloud_tenant'),
                               provider=provider,
                               network_manager=f'{provider.name} Network Manager',
                               has_external_gw=ext_gw,
                               ext_network=ext_network,
                               ext_network_subnet=ext_subnet)
    return router


@pytest.fixture(scope='function')
def network(provider, appliance):
    """Create cloud network"""
    network = create_network(appliance, provider, is_external=False)
    yield network
    delete_entity(network)


@pytest.fixture(scope='function')
def ext_network(provider, appliance):
    """Create external cloud network"""
    network = create_network(appliance, provider, is_external=True)
    yield network
    delete_entity(network)


@pytest.fixture(scope='function')
def subnet(provider, appliance, network):
    """Creates subnet for the given network"""
    subnet = create_subnet(appliance, provider, network)
    yield subnet
    delete_entity(subnet)


@pytest.fixture(scope='function')
def ext_subnet(provider, appliance, ext_network):
    """Creates subnet for the given external network"""
    subnet = create_subnet(appliance, provider, ext_network)
    yield subnet
    delete_entity(subnet)


@pytest.fixture(scope='function')
def router(provider, appliance):
    """Creates network router"""
    router = create_router(appliance, provider, ext_gw=False)
    yield router
    delete_entity(router)


@pytest.fixture(scope='function')
def router_with_gw(provider, appliance, ext_subnet):
    """Creates network router with external network as a gateway"""
    router = create_router(appliance, provider, ext_gw=True, ext_network=ext_subnet.network,
                           ext_subnet=ext_subnet.name)
    yield router
    delete_entity(router)


@pytest.mark.regression
def test_create_network(network, provider):
    """Creates private cloud network and verifies it's relationships

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    assert network.exists
    assert network.parent_provider.name == provider.name
    assert network.cloud_tenant == provider.data.get('provisioning').get('cloud_tenant')


@pytest.mark.regression
def test_edit_network(network):
    """Edits private cloud network's name

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    network.edit(name=fauxfactory.gen_alpha(12, start="edited_"))
    wait_for(network.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=10)
    wait_for(lambda: network.exists,
             delay=15, timeout=600, fail_func=network.browser.refresh)
    assert network.exists


@pytest.mark.regression
def test_delete_network(network):
    """Deletes private cloud network

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    network.delete()
    wait_for(network.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=10)
    wait_for(lambda: not network.exists,
             delay=15, timeout=600, fail_func=network.browser.refresh)
    assert not network.exists


@pytest.mark.regression
def test_create_subnet(subnet, provider):
    """Creates private subnet and verifies it's relationships

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    assert subnet.exists
    assert subnet.parent_provider.name == provider.name
    assert subnet.cloud_tenant == provider.data.get('provisioning').get('cloud_tenant')
    assert subnet.cidr == SUBNET_CIDR
    assert subnet.cloud_network == subnet.network
    assert subnet.net_protocol == 'ipv4'


@pytest.mark.regression
def test_edit_subnet(subnet):
    """Edits private subnet's name

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    subnet.edit(new_name=fauxfactory.gen_alpha(12, start="edited_"))
    wait_for(subnet.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=10)
    wait_for(lambda: subnet.exists, delay=15, timeout=600, fail_func=subnet.browser.refresh)
    assert subnet.exists


@pytest.mark.regression
def test_delete_subnet(subnet):
    """Deletes private subnet

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    subnet.delete()
    wait_for(subnet.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=20), timeout=800,
             delay=30)
    wait_for(lambda: not subnet.exists,
             delay=30, timeout=800, fail_func=subnet.browser.refresh)
    assert not subnet.exists


@pytest.mark.regression
def test_create_router(router, provider):
    """Create router without gateway

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    assert router.exists
    assert router.cloud_tenant == provider.data.get('provisioning').get('cloud_tenant')


@pytest.mark.regression
def test_create_router_with_gateway(router_with_gw, provider):
    """Creates router with gateway (external network)

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    assert router_with_gw.exists
    assert router_with_gw.cloud_tenant == provider.data.get('provisioning').get('cloud_tenant')
    assert router_with_gw.cloud_network == router_with_gw.ext_network


@pytest.mark.regression
def test_edit_router(router):
    """Edits router's name

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    router.edit(name=fauxfactory.gen_alpha(12, start="edited_"))
    wait_for(router.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=10)
    wait_for(lambda: router.exists,
             delay=15, timeout=600, fail_func=router.browser.refresh)
    assert router.exists


@pytest.mark.regression
def test_delete_router(router, appliance):
    """Deletes router

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    router.delete()
    wait_for(router.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=20), timeout=800,
             delay=30)
    navigate_to(appliance.collections.network_routers, 'All')
    wait_for(lambda: not router.exists,
             delay=30, timeout=800, fail_func=router.browser.refresh)
    assert not router.exists


@pytest.mark.regression
def test_clear_router_gateway(router_with_gw):
    """Deletes a gateway from the router

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    router_with_gw.edit(change_external_gw=False)
    wait_for(router_with_gw.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10),
             timeout=600, delay=10)
    router_with_gw.browser.refresh()
    view = navigate_to(router_with_gw, 'Details')
    wait_for(lambda: 'Cloud Network' not in view.entities.relationships.fields,
             delay=15, timeout=600, fail_func=router_with_gw.browser.refresh)
    assert 'Cloud Network' not in view.entities.relationships.fields


@pytest.mark.regression
def test_add_gateway_to_router(router, ext_subnet):
    """Adds gateway to the router

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    router.edit(change_external_gw=True, ext_network=ext_subnet.network,
                ext_network_subnet=ext_subnet.name)
    wait_for(router.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=10)
    wait_for(lambda: router.cloud_network == ext_subnet.network,
             delay=15, timeout=600, fail_func=router.browser.refresh)
    assert router.cloud_network == ext_subnet.network


@pytest.mark.regression
def test_add_interface_to_router(router, subnet):
    """Adds interface (subnet) to router

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    view = navigate_to(router, 'Details')
    subnets_count_before_adding = int(view.entities.relationships.get_text_of('Cloud Subnets'))
    router.add_interface(subnet.name)
    wait_for(router.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=20), timeout=800,
             delay=30)
    # TODO: verify the exact entities' names and relationships, not only count
    try:
        wait_for(lambda: int(view.entities.relationships.get_text_of('Cloud Subnets')) ==
                 (subnets_count_before_adding + 1),
                 delay=30, timeout=800, fail_func=router.browser.refresh)
    except TimedOutError:
        assert False, "After waiting an interface to the router is still not added"


@pytest.mark.regression
def test_list_networks(provider, appliance):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    networks = [n.label for n in provider.mgmt.api.networks.list()]
    displayed_networks = [n.name for n in appliance.collections.cloud_networks.all()]
    for n in networks:
        assert n in displayed_networks
