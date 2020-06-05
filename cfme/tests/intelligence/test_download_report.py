import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [test_requirements.report]


@pytest.fixture(scope="module")
def report(appliance):
    saved_report = appliance.collections.reports.instantiate(
        type="Configuration Management",
        subtype="Virtual Machines",
        menu_name="Hardware Information for VMs",
    ).queue(wait_for_finish=True)
    yield saved_report
    saved_report.delete(cancel=False)


@pytest.mark.parametrize("filetype", ["txt", "csv", "pdf"])
@pytest.mark.provider([InfraProvider], selector=ONE, scope="module")
def test_download_report(setup_provider_modscope, report, filetype):
    """Download the report as a file.

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/20h
    """
    if filetype == "pdf":
        view = navigate_to(report, "Details")
        # since multiple window handling is not possible, we just assert that the option is enabled.
        assert view.download.item_enabled("Print or export as PDF")
    else:
        report.download(filetype)
