"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.manual]


@test_requirements.general_ui
@pytest.mark.tier(1)
@pytest.mark.meta(coverage=[1532404])
def test_provider_summary_topology():
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/2h
        setup:
            1. Add an infra provider.
        testSteps:
            1. Navigate to provider's summary page.
            2. Click on topology.
        expectedResults:
            1.
            2. Provider Topology must be displayed.

    Bugzilla:
        1532404
    """
    pass
