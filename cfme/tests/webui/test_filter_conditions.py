import pytest

from cfme import test_requirements


pytestmark = [test_requirements.filtering]


@pytest.mark.manual
@pytest.mark.tier(0)
def test_create_filter_with_multiple_conditions():
    """
    Polarion:
        assignee: anikifor
        casecomponent: WebUI
        caseimportance: high
        initialEstimate: 1/5h
        setup:
            1. Navigate to Compute > Infrastructure > Providers.
            2. Click on Advanced Search Filter.
        testSteps:
            1. Create an expression with multiple types of condition. Eg: arg_1 AND arg_2 OR arg_3
        expectedResults:
            1. Expression must be created successfully.

    Bugzilla:
        1660460
    """
    pass
