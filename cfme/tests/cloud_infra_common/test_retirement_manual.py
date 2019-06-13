# -*- coding: utf-8 -*-
# pylint: skip-file
"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.ignore_stream('upstream'),
    pytest.mark.manual,
    test_requirements.retirement
]


@pytest.mark.tier(2)
def test_retire_infra_vms_folder():
    """
    test the retire funtion of vm on infra providers, at least two vm,
    retire now button vms page

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


def test_retirement_date_uses_correct_time_zone():
    """
    Bug 1565128 - Wrong timezone when selecting retirement time

    Bugzilla:
        1565128

    After saving VM retirement date/time (using both "Specific Date and
    Time" and "Time Delay from Now" options), the displayed Retirement
    Date has the correct date and time-zone appropriate time.

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/15h
        startsin: 5.9
        title: Retirement date uses correct time zone
    """
    pass


@pytest.mark.tier(2)
def test_retire_cloud_vms_date_folder():
    """
    test the retire funtion of vm on cloud providers, at leat two vm, set
    retirement date button from vms page(without notification)

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(2)
def test_retire_infra_vms_notification_folder():
    """
    test the retire funtion of vm on infra providers, select at least two
    vms and press retirement date button from vms main page and specify
    retirement warning period (1week, 2weeks, 1 months).

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(2)
def test_retire_infra_vms_date_folder():
    """
    test the retire funtion of vm on infra providers, at least two vm, set
    retirement date button from vms page(without notification)

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


def test_vms_retirement_state_field_is_capitalized_correctly():
    """
    Bug 1518926 - Inconsistent capitalization for Retirement State field

    Bugzilla:
        1518926

    When a VM is retiring or retired, the VM should show a "Retirement
    State" field, not "Retirement state".

    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/15h
        title: VM's Retirement State field is capitalized correctly
    """
    pass


@pytest.mark.tier(2)
def test_retire_cloud_vms_folder():
    """
    test the retire funtion of vm on cloud providers, at leat two vm,
    retire now button vms page

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(2)
def test_retire_cloud_vms_notification_folder():
    """
    test the retire funtion of vm on cloud providers, one vm, set
    retirement date button from vm summary page with notification for two
    vms for one of the period (1week, 2weeks, 1 months)

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass
