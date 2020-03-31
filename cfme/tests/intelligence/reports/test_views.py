import pytest
from widgetastic_patternfly import CandidateNotFound

from cfme import test_requirements
from cfme.common.provider import BaseProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.report,
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([BaseProvider], selector=ONE, scope="module"),
]


@pytest.fixture(scope="module")
def report(appliance):
    report = appliance.collections.reports.instantiate(
        type="Configuration Management",
        subtype="Virtual Machines",
        menu_name="Guest OS Information - any OS",
    ).queue(wait_for_finish=True)
    yield report
    report.delete_if_exists()


@pytest.mark.rhv3
@pytest.mark.parametrize(
    "view_mode",
    ["Hybrid View", "Graph View", "Tabular View"],
    ids=["hybrid", "graph", "tabular"],
)
def test_report_view(report, view_mode):
    """Tests provisioning via PXE
    Bugzilla: 1401560

    Metadata:
        test_flag: report

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/6h
    """
    try:
        view = navigate_to(report, "Details")
    except CandidateNotFound:
        # Sometimes report name is not loaded correctly in the tree and it shows
        # `Generating report` instead of showing proper saved_report name,
        # due to which CandidateNotFound error is raised. Refreshing the browser
        # shows proper saved_report name in the tree.
        report.browser.refresh()
        view = navigate_to(report, "Details")
    view.view_selector.select(view_mode)
    assert view.view_selector.selected == view_mode, f"View setting failed for {view}"
