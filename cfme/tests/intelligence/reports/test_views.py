# -*- coding: utf-8 -*-
import pytest

import cfme.web_ui.toolbar as tb
from cfme import test_requirements
from cfme.intelligence.reports.reports import CannedSavedReport
from utils.blockers import BZ
from utils.log import logger
from utils.providers import setup_a_provider as _setup_a_provider

pytestmark = [pytest.mark.tier(3),
              test_requirements.report]


@pytest.fixture(scope="module")
def setup_a_provider():
    _setup_a_provider(prov_class="infra", validate=True, check_existing=True)


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
def test_report_view(setup_a_provider, create_report, view):
    create_report.navigate()
    tb.select(view)
    assert tb.is_active(view), "View setting failed for {}".format(view)
