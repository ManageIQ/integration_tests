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
