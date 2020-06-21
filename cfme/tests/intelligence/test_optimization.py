from datetime import datetime

import pytest
from widgetastic.exceptions import RowNotFound
from widgetastic.utils import attributize_string

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

pytestmark = [test_requirements.report, pytest.mark.tier(1), pytest.mark.ignore_stream("5.10")]

REPORTS = [
    "Host CPU Trends (last week)",
    "Host Memory Trends (last week)",
    "Offline VMs with Snapshot",
    "Top CPU Consumers (weekly)",
    "Top Memory Consumers (weekly)",
    "VMs with Volume Free Space >= 75%",
]


@pytest.mark.meta(automates=[1769346, 1714197])
@pytest.mark.parametrize("menu_name", REPORTS, ids=[attributize_string(i) for i in REPORTS])
def test_generate_optimization_report(appliance, menu_name):
    """
    Bugzilla:
        1769346
        1714197

    Polarion:
        assignee: pvala
        initialEstimate: 1/8h
        casecomponent: Reporting
        tags: reports
        startsin: 5.11
        testSteps:
            1. Navigate to Overview > Optimization and queue the report with parametrized menu_name.
            2. Check if the report exists.
    """
    saved_report = appliance.collections.optimization_reports.instantiate(
        menu_name=menu_name
    ).queue()
    assert saved_report.exists


@pytest.mark.meta(automates=[1769333])
def test_delete_generated_report(appliance):
    """
    Bugzilla:
        1769333

    Polarion:
        assignee: pvala
        initialEstimate: 1/8h
        casecomponent: Reporting
        tags: reports
        startsin: 5.11
        testSteps:
            1. Queue an optimization report.
            2. Navigate to the Saved reports page and delete the report
            3. Check if the optimization saved report still exists
        expectedResults:
            1.
            2.
            3. Report runs value for the optimization report must decrease by 1.
    """
    optimization_report = appliance.collections.optimization_reports.instantiate(
        menu_name="Offline VMs with Snapshot"
    )
    opt_saved_report = optimization_report.queue()

    # Note the value of runs for later comparison
    old_run = optimization_report.runs

    # There is an inconsistency between the time format for Optimization Report and Intel Report,
    # to overcome that we pick the details from the SavedReport table so that it is easy to
    # instantiate a SavedReport using ReportsCollection.
    run_at_time = opt_saved_report.run_at.split()[1]

    if BZ(1769333).blocks:
        # convert run_at time from 12-hr to 24hr format
        run_at_time = datetime.strftime(
            datetime.strptime(
                f"{opt_saved_report.run_at.split()[1]} {opt_saved_report.run_at.split()[2]}",
                "%I:%M:%S %p",
            ),
            "%H:%M:%S",
        )

    view = navigate_to(optimization_report.collections.saved_reports, "All")

    # This asserts the report exists for SavedReports accordion.
    # If the report does not exist, RowNotFound error would be raised here.
    try:
        row = next(
            view.table.rows(
                run_at__contains=run_at_time,
                name__contains=opt_saved_report.parent.parent.menu_name
            )
        )
    except RowNotFound:
        pytest.fail("Saved Report does not exist.")

    # Assert the report exists for Reports accordion
    saved_report = appliance.collections.reports.instantiate(
        type="Operations",
        subtype="Virtual Machines",
        menu_name=opt_saved_report.parent.parent.menu_name,
    ).saved_reports.instantiate(
        run_datetime=row.run_at.text, queued_datetime=row.queued_at.text, candu=False
    )

    assert saved_report.exists
    saved_report.delete()

    # Assert the run value decreases after deleting the report
    assert optimization_report.runs < old_run

    assert not opt_saved_report.exists
