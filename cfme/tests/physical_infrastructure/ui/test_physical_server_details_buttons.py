# -*- coding: utf-8 -*-
import pytest
from cfme.common.physical_server_views import (
    PhysicalServerDetailsView,
)
from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.appliance.implementations.ui import navigate_to

# The max time that a single test has to perform the entire cycle of action
# in seconds (10 min)
TIMEOUT = 600

# The time interval to perform a verification of state change
# in seconds (1 min)
DELAY = 10

pytestmark = [pytest.mark.tier(3), pytest.mark.provider([LenovoProvider], scope="module")]


@pytest.fixture(scope="function")
def physical_server(appliance, provider, setup_provider):
    # Get and return the first physical server
    return appliance.collections.physical_servers.all(provider)[0]


# Configuration Button
def test_refresh_relationships(physical_server, provider):
    last_refresh = provider.last_refresh_date()
    physical_server.refresh(provider, handle_alert=True)
    assert last_refresh != provider.last_refresh_date()


# Power Button
def test_restart_management_controller(physical_server, provider):
    physical_server.restart_management_controller(wait_restart_bmc=True)
    view = provider.create_view(PhysicalServerDetailsView, physical_server)
    view.flash.assert_message('Requested Server restart_mgmt_controller for the selected server')


actions = [
    ("power_off", "power_state", "off"),
    ("power_on", "power_state", "on"),
    ("power_off_now", "power_state", "off"),
    ("restart", "power_state", "on"),
    ("restart_now", "power_state", "on"),
    ("restart_to_sys_setup", "power_state", "on"),
    ("blink_loc_led", "location_led_state", "Blinking"),
    ("turn_off_loc_led", "location_led_state", "Off"),
    ("turn_on_loc_led", "location_led_state", "On")
]


@pytest.mark.parametrize("action, attr, desired_state",
                         actions, ids=[action[0] for action in actions])
def test_server_actions(physical_server, provider, action, attr,
                        desired_state):
    """ Test the physical server actions sending the action request, waiting the task be complete on MiQ
        and then waiting the state of the some attribute of the physical server be changed
    Params:
        * action:        the action to be performed against the Physical Server
        * attr:          the physical server attribute that will be changed by the action
        * desired_state: the value of the attribute after the action execution
    Metadata:
        test_flag: crud
    """
    view = provider.create_view(PhysicalServerDetailsView, physical_server)
    getattr(physical_server, action)()

    message = 'Requested Server {} for the selected server'.format(action)
    view.flash.assert_message(message)
    physical_server.wait_for_state_change(desired_state, attr, provider, view, TIMEOUT, DELAY)


# Lifecycle Button
def test_lifecycle_provision(physical_server):
    view = navigate_to(physical_server, "Provision")
    assert view.is_displayed


# Monitoring Button
def test_monitoring_button(physical_server):
    view = navigate_to(physical_server, "Timelines")
    assert view.is_displayed
