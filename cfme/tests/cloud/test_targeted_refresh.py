import pytest

from cfme import test_requirements

pytestmark = [
    test_requirements.ec2,
]


@pytest.mark.manual
def test_ec2_targeted_refresh_instance():
    """
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1 1/6h
        startsin: 5.9
        testSteps:
            1. Instance CREATE
            2. Instance RUNNING
            3. Instance STOPPED
            4. Instance UPDATE
            5. Instance DELETE - or - Instance TERMINATE
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_floating_ip():
    """
    AWS naming is Elastic IP

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1 1/2h
        startsin: 5.9
        testSteps:
            1. Classic Floating IP Allocate
            2. VPC Floating IP Allocate
            3. Classic Floating IP Allocate to Instance (Check both IP and Instance)
            4. Classic Floating IP Allocate to Network Port (Check both IP and Port)
            5. VPC Floating IP Allocate to Instance (Check both IP and Instance)
            6. VPC Floating IP Allocate to Network Port (Check both IP and Port)
            7. Floating IP UPDATE
            8. Floating IP DELETE
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_network():
    """
    AWS naming is VPC

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
        testSteps:
            1. Network CREATE
            2. Network UPDATE
            3. Network DELETE
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_network_router():
    """
    AWS naming is Route Table

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
        testSteps:
            1. Network Router CREATE
            2. Network Router DELETE
            3. Network Router UPDATE
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_network_port():
    """
    AWS naming is Network Interface

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
        testSteps:
            1. Network port CREATE
            2. Network port UPDATE
            3. Assign private IP
            4. Unassign private IP
            5. Network port DELETE
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_stack():
    """
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/2h
        startsin: 5.9

        testSteps:
            1. Stack CREATE
            2. Stack DELETE
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_volume():
    """
    AWS naming is EBS

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 2/3h
        startsin: 5.9
        testSteps:
            1. Volume CREATE
            2. Volume UPDATE
            3. Volume DELETE
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_subnet():
    """
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
        testSteps:
            1. Subnet CREATE
            2. Subnet UPDATE
            3. Subnet DELETE
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_load_balancer():
    """
    AWS naming is ELB

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9
        testSteps:
            1. Apply Security group
            2. Floating IP CREATE
            3. Floating IP UPDATE
            4. Floating IP DELETE
    """
    pass


@pytest.mark.manual
def test_ec2_targeted_refresh_security_group():
    """
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 2/3h
        startsin: 5.9

        testSteps:
            1. Security group CREATE
            2. Security group UPDATE
            3. Security group DELETE
    """
    pass
