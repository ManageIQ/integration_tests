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


pytest_generate_tests = testgen.generate([OpenStackProvider],
                                         scope='module')

pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


@pytest.mark.yield_fixture(scope='function')
def network(provider):
    network = CloudNetwork(name=fauxfactory.gen_alpha(),
                           tenant=provider.get_yaml_data()['tenant'],
                           network_type='VXLAN')
    network.create()
    yield network
    # TODO: replace this with neutron client request
    network.delete()


def test_list_networks(provider, appliance):
    networks = provider.mgmt.list_network()
    displayed_networks = CloudNetworkCollection(appliance).all()
    for n in networks:
        assert n in displayed_networks


def test_create_network(network):
    assert network.network_type == network.type
