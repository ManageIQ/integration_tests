# -*- coding: utf-8 -*-
import pytest


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
def test_download_report(infra_provider, report, filetype):
    """Download the report as a file.

    Polarion:
        assignee: pvala
        casecomponent: report
        caseimportance: high
        initialEstimate: 1/20h
    """
    report.download(filetype)
