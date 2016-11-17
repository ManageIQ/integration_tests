# -*- coding: utf-8 -*-
import pytest

import cfme.web_ui.toolbar as tb
from cfme import test_requirements
from cfme.intelligence.reports.reports import CannedSavedReport
from utils import testgen
from utils.blockers import BZ
from utils.log import logger

pytestmark = [pytest.mark.tier(3),
              test_requirements.report,
              pytest.mark.usefixtures('setup_provider')]

pytest_generate_tests = testgen.generate(
    testgen.provider_by_type, ['openstack', 'ec2', 'rhevm', 'vsphere'],
    scope='module')


@pytest.yield_fixture(scope='module')
def create_report():
    # TODO parameterize on path, for now test infrastructure reports
    path = ["Configuration Management", "Hosts", "Virtual Infrastructure Platforms"]
    report = CannedSavedReport.new(path)
    report_time = report.datetime
    logger.debug('Created report for path {} and time {}'.format(path, report_time))
    yield report

    try:
        report.delete()
    except Exception:
        logger.warning('Failed to delete report for path {} and time {}'.format(path, report_time))


@pytest.mark.parametrize('view', ['Hybrid View', 'Graph View', 'Tabular View'])
@pytest.mark.meta(blockers=[BZ(1396220)])
def test_report_view(create_report, view):
    create_report.navigate()
    tb.select(view)
    assert tb.is_active(view), "View setting failed for {}".format(view)
