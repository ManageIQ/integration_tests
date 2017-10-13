"""Tests for Openstack cloud networks and subnets"""

import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.networks.cloud_network import CloudNetworkCollection
from cfme.utils import testgen


pytest_generate_tests = testgen.generate([OpenStackProvider, OpenstackInfraProvider],
                                         scope='module')

pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


def test_list_networks(provider, appliance):
    networks = [n.label for n in provider.mgmt.api.networks.list()]
    displayed_networks = [n.name for n in CloudNetworkCollection(appliance).all()]
    for n in networks:
        assert n in displayed_networks
