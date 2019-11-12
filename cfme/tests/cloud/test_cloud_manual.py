"""Manual tests"""
import pytest

from cfme import test_requirements


@pytest.mark.manual
@pytest.mark.tier(1)
@test_requirements.discovery
def test_add_cloud_provider_screen():
    """
    Polarion:
        assignee: pvala
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 3h
        setup:
            1. Navigate to Compute > Clouds > Providers.
            2. Click on `Configuration` and select `Add a new Cloud provider`.
        testSteps:
            1. Open Stack: test incorrect format of Hostname
            2. Open Stack: test incorrect Hostname
            3. Open Stack: test incorrect Security Protocol
            4. Open Stack: test switching Security Protocol
            5. Open Stack AMQP Event: test Hostname
            6. Open Stack AMQP Event: test incorrect format of Hostname
            7. Open Stack AMQP Event: test incorrect Hostname
            8. Open Stack AMQP Event: test API Port
            9. Open Stack AMQP Event: test incorrect format of API Port
            10. Open Stack AMQP Event: test incorrect API Port
            11. Open Stack AMQP Event: test Security Protocol
            12. Open Stack AMQP Event: test incorrect Security Protocol
            13. Open Stack AMQP Event: test Username
            14. Open Stack AMQP Event: test incorrect format of Username
            15. Open Stack AMQP Event: test incorrect Username
            16. Open Stack AMQP Event: test Password
            17. Open Stack AMQP Event: test incorrect format of Password
            18. Open Stack AMQP Event: test incorrect Password
            19. Open Stack AMQP Event: test Validate
            20. Open Stack AMQP Event: test switching Security Protocol
            21. Amazon EC2: test incorrect Region
            22. Amazon EC2: test incorrect format of Access Key ID
            23. Amazon EC2: test incorrect Access Key ID
            24. Amazon EC2: test incorrect format of Secret Access Key
            25. Amazon EC2: test incorrect Secret Access Key
            26. Azure: test incorrect Region
            27. Azure: test incorrect format of Tenant ID
            28. Azure: test incorrect Tenant ID
            29. Azure: test incorrect format of Subscription ID
            30. Azure: test incorrect Subscription ID
        expectedResults:
            1. Validation Error must be raised and provider must not be added.
            2. Validation Error must be raised and provider must not be added.
            3. Validation Error must be raised and provider must not be added.
            4. Validation Error must be raised and provider must not be added.
            5. Validation Error must be raised and provider must not be added.
            6. Validation Error must be raised and provider must not be added.
            7. Validation Error must be raised and provider must not be added.
            8. Validation Error must be raised and provider must not be added.
            9. Validation Error must be raised and provider must not be added.
            10. Validation Error must be raised and provider must not be added.
            11. Validation Error must be raised and provider must not be added.
            12. Validation Error must be raised and provider must not be added.
            13. Validation Error must be raised and provider must not be added.
            14. Validation Error must be raised and provider must not be added.
            15. Validation Error must be raised and provider must not be added.
            16. Validation Error must be raised and provider must not be added.
            17. Validation Error must be raised and provider must not be added.
            18. Validation Error must be raised and provider must not be added.
            19. Validation Error must be raised and provider must not be added.
            20. Validation Error must be raised and provider must not be added.
            21. Validation Error must be raised and provider must not be added.
            22. Validation Error must be raised and provider must not be added.
            22. Validation Error must be raised and provider must not be added.
            23. Validation Error must be raised and provider must not be added.
            24. Validation Error must be raised and provider must not be added.
            25. Validation Error must be raised and provider must not be added.
            26. Validation Error must be raised and provider must not be added.
            27. Validation Error must be raised and provider must not be added.
            28. Validation Error must be raised and provider must not be added.
            29. Validation Error must be raised and provider must not be added.
            30. Validation Error must be raised and provider must not be added.

    """
    pass


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
