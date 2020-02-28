import collections

import pytest

from cfme.common.physical_server_views import PhysicalServersView
from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for

pytestmark = [pytest.mark.tier(3), pytest.mark.provider([LenovoProvider], scope="module")]


@pytest.fixture(scope="function")
def physical_servers(appliance, provider, setup_provider):
    # Get and return all the physical servers
    return appliance.collections.physical_servers.all(provider)


@pytest.fixture(scope="function")
def physical_servers_collection(appliance):
    # Get and return collection of the physical servers
    return appliance.collections.physical_servers


# Configuration Button
def test_refresh_relationships(physical_servers_collection, physical_servers, provider):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    view = navigate_to(physical_servers_collection, "All")
    last_refresh = provider.last_refresh_date()
    item = "Refresh Relationships and Power States"
    physical_servers_collection.custom_button_action("Configuration", item, physical_servers)
    out, time = wait_for(
        lambda: last_refresh != provider.last_refresh_date(),
        fail_func=view.browser.refresh,
        message="Wait for the servers to be refreshed...",
        num_sec=300,
        delay=5
    )
    assert out


Action = collections.namedtuple('Action', 'button item method')
actions = [
    Action("Power", "Power Off", "power_off"),
    Action("Power", "Power On", "power_on"),
    Action("Power", "Power Off Immediately", "power_off_now"),
    Action("Power", "Restart", "restart"),
    Action("Power", "Restart Immediately", "restart_now"),
    Action("Power", "Restart to System Setup", "restart_to_sys_setup"),
    Action("Power", "Restart Management Controller", "restart_mgmt_controller"),
    Action("Identify", "Blink LED", "blink_loc_led"),
    Action("Identify", "Turn Off LED", "turn_off_loc_led"),
    Action("Identify", "Turn On LED", "turn_on_loc_led")
]


# Power / Identify Buttons
@pytest.mark.parametrize("button, item, method",
                         actions, ids=[action.item for action in actions])
def test_server_actions(physical_servers_collection, physical_servers, provider,
                        button, item, method):
    """ Test the physical server actions are creating a handler alert to each action of the a collection
    of physical servers.
    Params:
        * button: the button to be performed on the physical server list page
        * item: the item to be selected inside the dropdrown button
        * method: the name of the method that most be used to compare if was invoked the
        current method on the manageIQ.
    Metadata:
        test_flag: crud

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    view = provider.create_view(PhysicalServersView)

    last_part = 's' if len(physical_servers) > 1 else ''
    message = 'Requested Server {} for the selected server{}'.format(method, last_part)
    physical_servers_collection.custom_button_action(button, item, physical_servers)

    def assert_handler_displayed():
        if view.flash.is_displayed:
            return view.flash[0].text == message

        return False

    wait_for(
        assert_handler_displayed,
        message="Wait for the handler alert to appear...",
        num_sec=20,
        delay=5
    )
    view.browser.refresh()


# Policy Button
def test_manage_button(physical_servers_collection, physical_servers):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_servers_collection.select_entity_rows(physical_servers)
    view = navigate_to(physical_servers_collection, "ManagePoliciesCollection")
    assert view.is_displayed


def test_edit_tag(physical_servers_collection, physical_servers):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_servers_collection.select_entity_rows(physical_servers)
    view = navigate_to(physical_servers_collection, "EditTagsCollection")
    assert view.is_displayed


# Lifecycle Button
def test_lifecycle_provision(physical_servers_collection, physical_servers):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_servers_collection.select_entity_rows(physical_servers)
    view = navigate_to(physical_servers_collection, "ProvisionCollection")
    assert view.is_displayed
