# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.intelligence.reports.reports import CannedSavedReport
from cfme.utils.blockers import BZ
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.report,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([OpenStackProvider, EC2Provider, RHEVMProvider, VMwareProvider],
                         scope='module')
]


@pytest.yield_fixture(scope='module')
def report():
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


@pytest.mark.rhv3
@pytest.mark.parametrize('view_mode', ['Hybrid View', 'Graph View', 'Tabular View'])
@pytest.mark.meta(blockers=[BZ(1401560)])
def test_report_view(report, view_mode):
    view = navigate_to(report, 'Details')
    view.view_selector.select(view_mode)
    assert view.view_selector.selected == view_mode, "View setting failed for {}".format(view)
