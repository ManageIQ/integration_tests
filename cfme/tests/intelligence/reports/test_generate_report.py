# -*- coding: utf-8 -*-

""" This test generate one default report for each category under reports accordion

"""

import pytest

# from selenium.common.exceptions import NoSuchElementException

from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.intelligence.reports.reports import CannedSavedReport
from cfme.utils import testgen
from cfme import test_requirements
# from utils.log import logger

pytestmark = [pytest.mark.tier(3),
              test_requirements.report,
              pytest.mark.usefixtures('setup_provider')]

pytest_generate_tests = testgen.generate([VMwareProvider], scope='module')


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


@pytest.mark.parametrize('path', report_path, scope="module", ids=lambda param: '/'.join(param[:2]))
def test_reports_generate_report(request, path):
    """ This Tests run one default report for each category

    Steps:
        *Run one default report
        *Delete this Saved Report from the Database
    """

    report = CannedSavedReport.new(path)
    request.addfinalizer(report.delete_if_exists)
