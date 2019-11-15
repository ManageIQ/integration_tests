import pytest

from cfme.common.physical_server_views import (
    PhysicalServerDetailsView,
)
from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.tier(3), pytest.mark.provider([LenovoProvider], scope="module")]


@pytest.fixture(scope="module")
def physical_server(appliance, provider):
    # Get and return the first physical server
    ph_server = appliance.collections.physical_servers.all(provider)[0]
    return ph_server


# Configuration Button
def test_refresh_relationships(physical_server, provider):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    last_refresh = provider.last_refresh_date()
    physical_server.refresh(provider, handle_alert=True)
    assert last_refresh != provider.last_refresh_date()


# Power Button
def test_power_off(physical_server, provider):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_server.power_off()
    view = provider.create_view(PhysicalServerDetailsView, physical_server)
    view.flash.assert_message('Requested Server power_off for the selected server')


def test_power_on(physical_server, provider):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_server.power_on()
    view = provider.create_view(PhysicalServerDetailsView, physical_server)
    view.flash.assert_message('Requested Server power_on for the selected server')


def test_power_off_immediately(physical_server, provider):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_server.power_off_immediately()
    view = provider.create_view(PhysicalServerDetailsView, physical_server)
    view.flash.assert_message('Requested Server power_off_now for the selected server')


def test_restart(physical_server, provider):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_server.restart()
    view = provider.create_view(PhysicalServerDetailsView, physical_server)
    view.flash.assert_message('Requested Server restart for the selected server')


def test_restart_immediately(physical_server, provider):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_server.restart_immediately()
    view = provider.create_view(PhysicalServerDetailsView, physical_server)
    view.flash.assert_message('Requested Server restart_now for the selected server')


# Identify Button
def test_turn_on_led(physical_server, provider):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_server.turn_on_led()
    view = provider.create_view(PhysicalServerDetailsView, physical_server)
    view.flash.assert_message('Requested Server turn_on_loc_led for the selected server')


def test_turn_off_led(physical_server, provider):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_server.turn_off_led()
    view = provider.create_view(PhysicalServerDetailsView, physical_server)
    view.flash.assert_message('Requested Server turn_off_loc_led for the selected server')


def test_turn_blink_led(physical_server, provider):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    physical_server.turn_blink_led()
    view = provider.create_view(PhysicalServerDetailsView, physical_server)
    view.flash.assert_message('Requested Server blink_loc_led for the selected server')


# Lifecycle Button
def test_lifecycle_provision(physical_server):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    view = navigate_to(physical_server, "Provision")
    assert view.is_displayed


# Monitoring Button
def test_monitoring_button(physical_server):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    view = navigate_to(physical_server, "Timelines")
    assert view.is_displayed
