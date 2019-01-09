# -*- coding: utf-8 -*-
import pytest

timelines_reports = ('hosts', 'vm_operation', 'policy_events', 'policy_events2')


@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.parametrize('report', timelines_reports)
def test_default_reports_with_timelines(report):
    """
    Test that a timeline widget is displayed for the default reports.
    Note that since the default reports look at last week, to test, we modify the reports

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/5h
        casecomponent: web_ui
        caseimportance: medium
        testSteps:
            1. Add an infrastructure provider to ensure that an event for each report will occur
            2. Navigate to Cloud Intel -> Reports
            3. Modify one of the default reports to display events from today
            4. Navigate to Cloud Intel -> Timelines
            5. Click on the report you created
            6. Verify that the timeline (with events) is properly displayed
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.parametrize('report', timelines_reports)
def test_custom_reports_with_timelines(report):
    """
    Test that a timeline widget is displayed for custom reports.

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/5h
        casecomponent: web_ui
        caseimportance: medium
        testSteps:
            1. Add an infrastructure provider to ensure that an event for each report will occur
            2. Navigate to Cloud Intel -> Reports
            3. Create a custom report for each of the parameters
            4. Navigate to Cloud Intel -> Timelines
            5. Click on the report you created
            6. Verify that the timeline (with events) is properly displayed
    """
    pass
