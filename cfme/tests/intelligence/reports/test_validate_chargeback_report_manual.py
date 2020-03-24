"""Manual chargeback tests"""
import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.ignore_stream('upstream'),
    pytest.mark.manual,
    test_requirements.chargeback,
]


@pytest.mark.parametrize('report_period', ['daily_report', 'weekly_report', 'monthly_report'])
@pytest.mark.parametrize('rate_period', ['hourly_rate', 'weekly_rate', 'monthly_rate'])
@pytest.mark.parametrize('resource', ['cpu', 'network', 'disk', 'memory'])
def test_validate_chargeback_cost(report_period, rate_period, resource):
    """
    Validate resource usage cost.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.parametrize('resource', ['cpu', 'memory', 'storage'])
def test_chargeback_resource_allocation(resource):
    """
    Verify resource allocation in a chargeback report.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/10h
    """
    pass


@pytest.mark.tier(3)
def test_saved_chargeback_report_show_full_screen():
    """
    Verify that saved chargeback reports can be viewed

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass
