import pytest

from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.rest import assert_response
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([LenovoProvider], scope='module')
]

# The max time that a single test has to perform the entire cycle of action
# in seconds (5 min)
TIMEOUT = 600

# The time interval to perform a verification of state change
# in seconds (1 min)
DELAY = 60


@pytest.fixture(scope="module")
def physical_server(appliance, provider, setup_provider_modscope):
    try:
        physical_server = appliance.rest_api.collections.physical_servers.filter(
            {"provider": provider}
        ).all()[0]
    except IndexError:
        pytest.skip('No physical server on provider')
    except AttributeError:
        pytest.skip('No physical server attribute in REST collection')
    return physical_server


def get_server_attr(attr_name, provider, physical_server):
    provider.refresh_provider_relationships()
    physical_server.reload()
    return physical_server[attr_name]


def test_get_physical_server(physical_server, appliance):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    existent_server = appliance.rest_api.get_entity('physical_servers', physical_server.id)
    existent_server.reload()
    assert_response(appliance)


def test_get_nonexistent_physical_server(appliance):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    nonexistent = appliance.rest_api.get_entity('physical_servers', 999999)
    with pytest.raises(Exception, match='ActiveRecord::RecordNotFound'):
        nonexistent.reload()
    assert_response(appliance, http_status=404)


def test_invalid_action(physical_server, appliance):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    payload = {
        "action": "invalid_action"
    }
    with pytest.raises(Exception, match='Api::BadRequestError'):
        appliance.rest_api.post(physical_server.href, **payload)


def test_refresh_physical_server(appliance, physical_server):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Rest
        initialEstimate: 1/4h
    """
    assert getattr(physical_server.action, "refresh")()
    assert_response(appliance)


actions = [
    ("power_off", "power_state", "off"),
    ("power_on", "power_state", "on"),
    ("power_off_now", "power_state", "off"),
    ("restart", "power_state", "on"),
    ("restart_now", "power_state", "on"),
    ("blink_loc_led", "location_led_state", "Blinking"),
    ("turn_on_loc_led", "location_led_state", "On"),
    ("turn_off_loc_led", "location_led_state", "Off")
]


@pytest.mark.parametrize("action, verification_attr, desired_state",
                         actions, ids=[action[0] for action in actions])
def test_server_actions(physical_server, appliance, provider, action,
                        verification_attr, desired_state):
    """ Test the physical server actions sending the action request, waiting the task be complete on MiQ
        and then waiting the state of some attribute of physical server be change
    Params:
        * action:            the action to be perform against the Physical Server
        * verification_attr: the physical server attribute that will be change by the action
        * desired_state:     the value of the attribute after the action execution
    Metadata:
        test_flag: rest

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Rest
        initialEstimate: 1/4h
    """

    def condition():
        server_attr = get_server_attr(verification_attr, provider, physical_server)
        return server_attr.lower() == desired_state.lower()

    assert getattr(physical_server.action, action)()
    assert_response(appliance)
    wait_for(condition, num_sec=TIMEOUT, delay=DELAY)
