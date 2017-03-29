# -*- coding: utf-8 -*-
import pytest
from utils import testgen
from cfme.intelligence.reports.reports import CannedSavedReport
from collections import namedtuple


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")


DataSet = namedtuple('DataSet', ('menu_name', 'report_fields'))

DATA_SETS = [DataSet('Nodes By Capacity',
                     ('Name', 'CPU Cores', 'Memory')),
             DataSet('Nodes By CPU Usage',
                     ('Name', 'CPU Usage (%)')),
             DataSet('Nodes By Memory Usage',
                     ('Name', 'Memory Usage (%)')),
             DataSet('Recently Discovered Pods',
                     ('Name', 'Ready Status', 'Creation')),
             DataSet('Number of Nodes per CPU Cores',
                     ('Number of Nodes per CPU Cores', 'Hardware Number of CPU Cores')),
             DataSet('Pods per Ready Status',
                     ('# Pods per Ready Status', 'Ready Condition Status')),
             DataSet('Projects by Number of Pods',
                     ('Project Name', 'Number of Pods')),
             DataSet('Projects By CPU Usage',
                     ('Name', 'CPU Usage (%)')),
             DataSet('Projects By Memory Usage',
                     ('Name', 'Memory Usage (%)'))]


#  CMP-9132 CMP-9133 CMP-9134 CMP-9135 CMP-9136 CMP-9137


@pytest.mark.parametrize('cls', DATA_SETS, ids=[cls.menu_name for cls in DATA_SETS])
def test_containers_reports(cls):
    """Testing containers reports creation and verify headers (fields).

    Steps:
        * In CFME: Select Cloud Intelligence --> Reports.
          Reports drop down --> Configuration Management --> Containers -> <cls.menu_name>.
        * Generate report (Queue).

    Expected result:
        * Report created successfully and has its all fields.
    """
    path_to_report = ['Configuration Management', 'Containers',
                      cls.menu_name]
    run_at = CannedSavedReport.queue_canned_report(path_to_report)
    report = CannedSavedReport(path_to_report, run_at)
    assert report.data.headers == cls.report_fields
    #  TODO: Add functionality to verify that the fields of each reports are correct
