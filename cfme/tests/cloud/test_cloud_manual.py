"""Manual tests"""
import pytest

from cfme import test_requirements


@test_requirements.ec2
@pytest.mark.manual('manualonly')
def test_ec2_flavor_list_up_to_date():
    """
    Requirement: EC2 Provider

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/3h
        caseimportance: high
        casecomponent: Cloud
        testSteps:
            1. Go to Compute -> Cloud -> Instances
            2. Try to provision an HVM instance
            3. Go to Properties and compare hvm instance types with HVM instance
            types in AWS console.
            4. Try to provision an paravirtual instance
            5. Go to Properties and compare paravirtual instance types with
            paravirtual instance types in AWS console.
        expectedResults:
            1.
            2.
            3. AWS console instance types list should be equal to instance types in CFME
            4.
            5. AWS console instance types list should be equal to instance types in CFME
    """
    pass
