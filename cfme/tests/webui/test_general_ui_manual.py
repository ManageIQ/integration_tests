# -*- coding: utf-8 -*-
# pylint: skip-file
"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.ignore_stream('upstream'),
    pytest.mark.manual,
    test_requirements.general_ui
]


def test_notification_window_events_show_in_timestamp_order():
    """
    Bug 1469534 - The notification events are out of order

    Bugzilla:
        1469534

    If multiple event notifications are created near-simultaneously (e.g.,
    several VM"s are provisioned), then clicking on the bell icon in the
    top right of the web UI displays the event notifications in timestamp
    order.

    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/4h
        startsin: 5.9
        title: Notification window events show in timestamp order
    """
    pass


def test_notification_window_can_be_closed_by_clicking_x():
    """
    Bug 1427484 - Add "X" option to enable closing the Notification window
    by it.

    Bugzilla:
        1427484

    After clicking the bell icon in the top right of the web UI, the "x"
    in the top right corner of the notification window can be clicked to
    close it.

    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/15h
        startsin: 5.9
        title: Notification window can be closed by clicking 'x'
    """
    pass


@pytest.mark.manual('manualonly')
@pytest.mark.tier(1)
def test_infrastructure_provider_left_panel_titles():
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/18h
        testSteps:
            1. Add an infrastructure provider and navigate to it's Details page.
            2. Select Properties on the panel and check all items, whether they have their titles.
            3. Select Relationships on the panel and check all items,
                whether they have their titles.
        expectedResults:
            1.
            2. Properties panel must have all items and clicking on each item should display
                the correct page.
            3. Relationships panel must have all items and clicking on each item should display
                the correct page.
    """
    pass


@pytest.mark.manual
def test_infrastructure_hosts_icons_states():
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/3h
        setup:
            1. Add a RHEVM provider.
            2. SSH into appliance console and run `psql vmdb_production`
        testSteps:
            1. Check if the Quadicon and host power_state changes after running the command:
                UPDATE hosts SET power_state = 'preparing_for_maintenance' WHERE
                name='NAME OF THE TESTED HOST';
            2. Check if the Quadicon and host power_state changes after running the command:
                UPDATE hosts SET power_state = 'maintenance' WHERE name='NAME OF THE
                TESTED HOST';
            3. Check if the Quadicon and host power_state changes after running the command:
                UPDATE hosts SET power_state = 'unknown' WHERE name='NAME OF THE
                TESTED HOST';
            4. Check if the Quadicon and host power_state changes after running the command:
                UPDATE hosts SET power_state = 'on' WHERE name='NAME OF THE TESTED
                HOST';
            5. Check if the Quadicon and host power_state changes after running the command:
                UPDATE hosts SET power_state = 'off' WHERE name='NAME OF THE TESTED
                HOST';
        expectedResults:
            1. Quadicon and power_state must change to `preparing_for_maintence`
            2. Quadicon and power_state must change to `maintence`
            3. Quadicon and power_state must change to `unknown`
            4. Quadicon and power_state must change to `on`
            5. Quadicon and power_state must change to `off`
    """
    pass
