import pytest

from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.tier(3),
    pytest.mark.provider([LenovoProvider])]


def test_physical_overview_page(appliance, setup_provider):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    providers = appliance.collections.physical_providers
    view = navigate_to(providers, 'Overview')
    assert view.is_displayed


def test_physical_overview_servers_number(appliance, provider):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    providers = appliance.collections.physical_providers
    servers = provider.mgmt.list_servers()
    view = navigate_to(providers, 'Overview')
    assert view.servers.value == len(servers)


def test_physical_overview_switches_number(appliance):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    providers = appliance.collections.physical_providers
    switches = appliance.collections.physical_switches.all()
    view = navigate_to(providers, 'Overview')
    assert view.switches.value == len(switches)
