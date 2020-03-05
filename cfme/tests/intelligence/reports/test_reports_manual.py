"""Manual tests"""
import pytest

from cfme import test_requirements
from cfme.utils.appliance import ViaREST
from cfme.utils.appliance import ViaUI


pytestmark = [pytest.mark.manual]


@test_requirements.report
@test_requirements.multi_region
@pytest.mark.tier(2)
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
@pytest.mark.parametrize('report', ['new-report', 'existing-report'])
def test_reports_in_global_region(context, report):
    """
    This test case tests report creation and rendering from global region
    based on data from remote regions.

    Polarion:
        assignee: tpapaioa
        casecomponent: Reporting
        caseimportance: critical
        initialEstimate: 1/2h
        testSteps:
            1. Set up Multi-Region deployment with 2 remote region appliances
            2. Add provider to each remote appliance
            3. Create and render report in global region. report should use data from both providers
            4. Use one of existing reports using data from added providers
        expectedResults:
            1.
            2.
            3. Report should be created and rendered successfully and show expected data.
            4. Report should be rendered successfully and show expected data.

    """
    pass


@pytest.mark.ignore_stream("5.10")
@test_requirements.report
@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1714197])
def test_optimization_reports():
    """
    Bugzilla:
        1714197

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/2h
        startsin: 5.11
        testSteps:
            1. Navigate to Overview > Optimization.
            2. Queue all the 7 parametrized reports and check if it exists.
        expectedResults:
            1.
            2. Reports must exist.
    """
    pass
