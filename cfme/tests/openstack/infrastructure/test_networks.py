"""Tests for Openstack cloud networks and subnets"""

import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider


pytestmark = [
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([OpenStackProvider, OpenstackInfraProvider],
                         scope='module'),
]


def test_list_networks(provider, appliance):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    networks = [n.label for n in provider.mgmt.api.networks.list()]
    displayed_networks = [n.name for n in appliance.collections.cloud_networks.all()]
    for n in networks:
        assert n in displayed_networks
