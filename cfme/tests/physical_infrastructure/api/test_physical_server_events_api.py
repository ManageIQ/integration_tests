import pytest

from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.rest import assert_response
from cfme.utils.wait import wait_for

# The max time in which the full test must complete
# in seconds (5 min)
TIMEOUT = 300

# The time interval to perform a verification of state change
# in seconds (1 min)
DELAY = 60

# All sources from all currently available physical infrastructure
# providers
SOURCES = ['LenovoXclarity']

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([LenovoProvider], scope="module")
]


@pytest.fixture(scope="module")
def physical_server(setup_provider_modscope, appliance):
    physical_server = appliance.rest_api.collections.physical_servers[0]
    return physical_server


def enumerate_physical_infra_provider_events(appliance):
    return sum([enumerate_events_from_source(appliance, x) for x in SOURCES])


def enumerate_events_from_source(appliance, source):
    return appliance.rest_api.collections.event_streams.find_by(source=source).count


def enumerate_events_and_refresh_physical_infra_provider(appliance, provider):
    event_count = enumerate_physical_infra_provider_events(appliance)
    provider.refresh_provider_relationships()
    return event_count


def test_get_physical_infra_provider_power_event(appliance, physical_server, provider):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    previous_num_events = enumerate_physical_infra_provider_events(appliance)
    physical_server.action.restart_now()
    assert_response(appliance)
    wait_for(
        lambda: enumerate_events_and_refresh_physical_infra_provider(
            appliance, provider
        ) > previous_num_events,
        num_sec=TIMEOUT, delay=DELAY
    )
