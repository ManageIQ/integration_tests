# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.common.provider import BaseProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.report,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([BaseProvider], selector=ONE, scope='module')
]


@pytest.fixture(scope='module')
def report(appliance):
    # TODO parameterize on path, for now test infrastructure reports
    report = appliance.collections.reports.instantiate(
        type="Configuration Management",
        subtype="Hosts",
        menu_name="Virtual Infrastructure Platforms"
    ).queue(wait_for_finish=True)
    yield report
    if report.exists:
        report.delete()


@pytest.mark.rhv3
@pytest.mark.parametrize('view_mode', ['Hybrid View', 'Graph View', 'Tabular View'])
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
    view = navigate_to(report, 'Details', force=True)
    view.view_selector.select(view_mode)
    assert view.view_selector.selected == view_mode, "View setting failed for {}".format(view)
