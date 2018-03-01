# -*- coding: utf-8 -*-
import pytest

from cfme.utils import testgen
from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.wait import wait_for
from cfme.utils.log import logger

pytestmark = [pytest.mark.tier(3)]

pytest_generate_tests = testgen.generate([LenovoProvider], scope="module")

"""
The max time that a single test has to perform the entire cycle of action
"""
TIMEOUT = 10000 # in seconds
"""
The time interval to perform a verification of state change
"""
DELAY = 10 # in seconds

@pytest.yield_fixture(scope="module")
def physical_server(provider, appliance):
    if not provider.exists:
        provider.create_rest()
        provider.refresh_provider_relationships
        physical_server = appliance.rest_api.collections.physical_servers[0]
    yield physical_server


def do_post_physical_server(params, appliance, physical_server):
    """
    Do post againist a single physical server
    """
    appliance.rest_api.post(physical_server.href, **params)
    return appliance.rest_api.response.ok


def perform_physical_server_action(action, appliance, physical_server):
    """
    Perform an action againist a single physical server
    """
    payload = {
        "action" : action
    }
    return do_post_physical_server(payload, appliance, physical_server)


def get_server_attr(attr_name, appliance, physical_server):
    physical_server.reload()
    return physical_server[attr_name]


def wait_for_power_state_change(state, appliance, server):
    wait_for(
        lambda: get_server_attr("power_state", appliance, server) == state, num_sec=TIMEOUT, delay=DELAY
    )


def wait_for_loc_led_state_change(state, appliance, server):
    wait_for(
        lambda: get_server_attr("location_led_state", appliance, server) == state, num_sec=TIMEOUT, delay=DELAY
    )


def verify_attribute(server, attribute, value):
    server.reload()
    return server[attribute] == value


def test_refresh_physical_server(appliance, physical_server):
    assert perform_physical_server_action("refresh", appliance, physical_server)


@pytest.mark.parametrize("action, desired_state",[
    ("power_on", "on"),
    ("power_off", "off"),
    ("power_off_now", "off"),
    ("restart", "on"),
    ("restart_now", "on"),
    ("restart_to_sys_setup", "on"),
    ("restart_mgmt_controller", "on")
])
def test_server_actions(physical_server, appliance, action, desired_state):
    assert perform_physical_server_action(action, appliance, physical_server)
    wait_for_power_state_change(desired_state, appliance, physical_server)
    assert verify_attribute(physical_server, "power_state", desired_state)


@pytest.mark.parametrize("action, desired_state",[
    ("blink_loc_led", "Blinking"),
    ("turn_on_loc_led", "On"),
    ("turn_off_loc_led", "Off")
])
def test_server_led_actions(physical_server, appliance, action, desired_state):
    assert perform_physical_server_action(action, appliance, physical_server)
    wait_for_loc_led_state_change(desired_state, appliance, physical_server)
    assert verify_attribute(physical_server, "location_led_state" ,desired_state)
