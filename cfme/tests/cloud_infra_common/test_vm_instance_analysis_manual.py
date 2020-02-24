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


@pytest.mark.meta(coverage=[1557452])
@pytest.mark.manual("manualonly")
def test_ssa_vm_ec2_agent_tracker():
    """
    Bugzilla:
        1557452

    Polarion:
        assignee: sbulage
        casecomponent: SmartState
        initialEstimate: 1/3h
        startsin: 5.9
        tags: smartstate
        testSteps:
            1. Add EC2 Provider.
            2. Update SmartState Docker credentials.
            3. Update Docker URL to docker.io with Satoe's Private Docker Image
            in appliance configuration
            4. Run ssa on Instance.
        expectedResults:
            1.
            2.
            3.
            4. Watch evm.log for Agent installation. Check the SSA gathers all information
            of instance like Users, Groups, Files etc.
    """
    pass
