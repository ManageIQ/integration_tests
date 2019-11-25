""" This test generate one default report for each category under reports accordion

"""
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE
# from selenium.common.exceptions import NoSuchElementException
# from utils.log import logger


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.report,
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.provider([InfraProvider], scope='module', selector=ONE),
]


report_path = [
    ["Configuration Management", "Virtual Machines", "Guest OS Information - any OS"],
    ["Migration Readiness", "Virtual Machines", "Summary - VMs migration ready"],
    ["Operations", "Virtual Machines", "VMs not Powered On"],
    ["VM Sprawl", "Candidates", "Summary of VM Create and Deletes"],
    ["Relationships", "Virtual Machines, Folders, Clusters", "VM Relationships"],
    ["Events", "Operations", "Events for VM prod_webserver"],
    ["Performance by Asset Type", "Virtual Machines", "Top CPU Consumers (weekly)"],
    ["Running Processes", "Virtual Machines", "Processes for prod VMs sort by CPU Time"],
    ["Trending", "Clusters", "Cluster CPU Trends (last week)"],
    ["Tenants", "Tenant Quotas", "Tenant Quotas"],
    ["Provisioning", "Activity Reports", "Provisioning Activity - by VM"],
]


@pytest.mark.rhel_testing
@pytest.mark.parametrize('path', report_path, scope="module", ids=lambda param: '/'.join(param[:2]))
def test_reports_generate_report(request, path, appliance):
    """ This Tests run one default report for each category

    Steps:
        *Run one default report
        *Delete this Saved Report from the Database

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/16h
    """
    report = appliance.collections.reports.instantiate(
        type=path[0],
        subtype=path[1],
        menu_name=path[2]
    ).queue(wait_for_finish=True)
    request.addfinalizer(report.delete_if_exists)

    assert report.exists
