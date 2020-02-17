import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.manual,
    pytest.mark.tier(2),
    test_requirements.smartstate,
]


@pytest.mark.meta(coverage=[1646467])
def test_provider_refresh_after_ssa():
    """
    Verify that system info obtained by ssa isn't wiped out after provider refresh

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/2h
        tags: smartstate
        testSteps:
            1. Add a Provider.
            2. provision vm or take one of its images
            3. run ssa on that vm or image
            4. kick off provider refresh
        expectedResults:
            1.
            2.
            3. system os and etc is fulfilled for that vm/image
            4. vm/system info hasn't been wiped out by provider refresh
    """
