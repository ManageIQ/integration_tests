# pylint: skip-file
"""Manual tests"""
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE

pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.manual,
    test_requirements.general_ui,
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
    """
    pass


@pytest.mark.manual("manualonly")
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


@pytest.mark.manual("manualonly")
@pytest.mark.tier(1)
@pytest.mark.meta(coverage=[1651194, 1503213])
@test_requirements.general_ui
@pytest.mark.provider([InfraProvider, CloudProvider], selector=ONE)
def test_pdf_summary_provider(provider):
    """
    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/8h
        testSteps:
            1. Add an Provider.
            2. Open the summary page of the provider
            3. In the toolbar check if "Print or export summary" button is displayed.
            4. Download the summary and check if Quadicon is shown correctly, exactly as in the UI.
        expectedResults:
            1.
            2.
            3. Button must be visible.
            4. Quadicon must be same as seen in'

    Bugzilla:
        1651194
        1503213
    """
    pass


@pytest.mark.manual("manualonly")
@pytest.mark.tier(1)
@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(coverage=[1740131])
def test_red_hat_cloud_page_internal_server_error():
    """
    Bugzilla:
        1740131

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/18h
        startsin: 5.11
        setup:
            1. Enable Internet Connectivity role
            2. Register the appliance
        testSteps:
            1. Navigate to Red Hat Cloud > Providers
        expectedResults:
            1. There should be no 500 Internal Server Error
    """
    pass


@pytest.mark.tier(1)
@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(coverage=[1741030])
def test_provider_documentation():
    """
    Bugzilla:
        1741030

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/18h
        startsin: 5.11
        setup:
            1. Take a fresh appliance with no provider
        testSteps:
            1. Log into the appliance and check where the link provided
                in `Learn more about this in the documentation.` points to.
        expectedResults:
            1. Link must point to downstream documentation and not upstream.
    """
    pass


@pytest.mark.tier(1)
@pytest.mark.meta(coverage=[1745660])
def test_compliance_column_header():
    """
    Bugzilla:
        1745660

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/18h
        setup:
            1. Add a infra/cloud provider
        testSteps:
            1. Navigate to All VMs/Instances page.
            2. Select the List View
            3. Click on the Compliance Column Header
        expectedResults:
            1.
            2.
            3. There should be no 500 Internal Server Error and the page must be displayed as is.
    """
    pass


@pytest.mark.tier(1)
@pytest.mark.meta(coverage=[1733120])
def test_compare_vm_from_datastore_relationships():
    """
    Bugzilla:
        1733120

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/18h
        setup:
            1. Add an infra provider.
        testSteps:
            1. Select a datastore with at least 2 VMS, and navigate to a it's Details page.
            2. Click on Managed VMs from the relationships table.
            3. Select at least 2 VMs and click on `Configuration > Compare the selected items`
        expectedResults:
            1.
            2.
            3. Comparison page should be displayed, there should be no exception on the page.
    """
    pass
