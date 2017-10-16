"""Tests for Openstack cloud networks and subnets"""

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


@pytest.yield_fixture(scope='function')
def network(provider, appliance):
    collection = appliance.collections.cloud_networks
    network = collection.create(name=fauxfactory.gen_alpha(),
                                tenant=provider.get_yaml_data()['tenant'],
                                provider=provider,
                                network_type='VXLAN',
                                network_manager='{} Network Manager'.format(provider.name))
    yield network
    # TODO: replace this with neutron client request
    try:
        if network.exists:
            network.delete()
    except Exception:
        logger.warning('Exception during network deletion - skipping..')


@pytest.fixture(scope='module')
def subnet_cidr():
    return '11.11.11.0/24'


@pytest.yield_fixture(scope='function')
def subnet(provider, appliance, network, subnet_cidr):
    collection = appliance.collections.network_subnets
    subnet = collection.create(name=fauxfactory.gen_alpha(),
                               tenant=provider.get_yaml_data()['tenant'],
                               provider=provider,
                               network_manager='{} Network Manager'.format(provider.name),
                               network_name=network.name,
                               cidr=subnet_cidr)
    yield subnet
    # TODO: replace this with neutron client request
    try:
        if subnet.exists:
            subnet.delete()
    except Exception:
        logger.warning('Exception during network subnet deletion - skipping..')


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
    wait_for(subnet.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600,
             delay=15)
    subnet.browser.refresh()
    assert not subnet.exists

# def test_create_router():
#
# def test_connect_inteface_to_router():
#
# def test_edit_router()
#
#
# def test_delete_router()
#
