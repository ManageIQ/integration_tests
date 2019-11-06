import pytest
from widgetastic.utils import attributize_string

from cfme import test_requirements
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


@pytest.mark.meta(automates=[1769346])
@pytest.mark.uncollectif(
    lambda menu_name: menu_name in ["Top CPU Consumers (weekly)", "Top Memory Consumers (weekly)"]
    and BZ(1769346, forced_streams=["5.11"]).blocks,
    reason="Breadcrumb for these reports is incorrect which is why the exists method fails.",
)
@pytest.mark.parametrize("menu_name", REPORTS, ids=[attributize_string(i) for i in REPORTS])
def test_generate_optimization_report(appliance, menu_name):
    """
    Bugzilla:
        1769346

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


@pytest.mark.manual
@pytest.mark.meta(coverage=[1769333])
def test_delete_generated_report():
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
    pass
