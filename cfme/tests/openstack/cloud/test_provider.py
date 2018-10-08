"""Tests for Openstack cloud provider"""

import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([OpenStackProvider], scope='function')
]


CARDS = [("Flavors", "list_flavor"), ("Images", "list_templates"),
         ("Cloud Networks", "list_network"),
         ("Instances", "list_vms"), ("Cloud Volumes", "list_volume")]


@pytest.mark.ignore_stream('5.9')
@pytest.mark.parametrize('card, api', CARDS)
def test_cloud_provider_cards(provider, card, api):
    view = navigate_to(provider, 'Details')
    view.toolbar.view_selector.select('Dashboard View')
    dashboard_card = view.entities.cards(card)
    attr = getattr(provider.mgmt, api)
    assert dashboard_card.value == len(attr())


@pytest.mark.ignore_stream('5.9')
def test_dashboard_card_availability_zones(provider):
    view = navigate_to(provider, 'Details')
    view.toolbar.view_selector.select('Dashboard View')
    dashboard_card = view.entities.cards("Availability Zones")
    assert dashboard_card.value == len(provider.mgmt.api.availability_zones.list())
