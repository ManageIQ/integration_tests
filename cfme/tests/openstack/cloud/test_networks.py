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
    collection = CloudNetworkCollection(appliance)
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


def test_create_network(network, provider):
    assert network.parent_provider.name == provider.name
    assert network.cloud_tenant == provider.get_yaml_data()['tenant']


def test_edit_network(network):
    network.edit(name=fauxfactory.gen_alpha())
    wait_for(network.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    network.browser.refresh()
    view = navigate_to(network, 'Details')
    name = view.entities.properties.get_text_of('Name')
    assert network.name == name


def test_delete_network():
    network.delete()
    wait_for(network.provider_obj.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    assert not network.exists

# def test_create_subnet():
#
#
# def test_create_router():
#
# def test_connect_inteface_to_router():
#
# def test_edit_router()
#
#
#
# def test_edit_subnet()
#
#
#
# def test_delete_subnet()
#
# def test_delete_router()
#
