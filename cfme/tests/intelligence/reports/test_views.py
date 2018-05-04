# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.blockers import BZ
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.report,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([OpenStackProvider, EC2Provider, RHEVMProvider, VMwareProvider],
                         scope='module')
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
@pytest.mark.meta(blockers=[BZ(1401560)])
def test_report_view(report, view_mode):
    view = navigate_to(report, 'Details')
    view.view_selector.select(view_mode)
    assert view.view_selector.selected == view_mode, "View setting failed for {}".format(view)
