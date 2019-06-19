import pytest

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.utils.generators import random_vm_name
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.ec2,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider(
        [EC2Provider],
        scope='module'
    )
]


def wait_for_power_state(vms_collection, instance_name, power_state):
    wait_for(lambda: vms_collection.get(name=instance_name)["power_state"] == power_state, delay=15,
             timeout=900, handle_exception=True)


def test_targeted_refresh_instance(appliance, provider):
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
            5. Instance RUNNING
            6. Instance DELETE - or - Instance TERMINATE
    """
    vms_collection = appliance.rest_api.collections.vms
    flavors_collection = appliance.rest_api.collections.flavors

    # create
    template_id = provider.mgmt.get_template(
        provider.data.templates.get('small_template').name).uuid
    instance = provider.mgmt.create_vm(template_id, vm_name=random_vm_name('refr'))

    # running
    wait_for_power_state(vms_collection, instance.name, "on")

    # stopped
    instance.stop()
    wait_for_power_state(vms_collection, instance.name, "off")

    # update
    instance.rename(random_vm_name('refr'))
    instance.change_type('t1.small')
    wait_for(lambda: flavors_collection.get(id=vms_collection.get(name=instance.name)["flavor_id"])
        ["name"] == instance.type, delay=15, timeout=900, handle_exception=True)

    # start
    instance.start()
    wait_for_power_state(vms_collection, instance.name, "on")

    # delete
    instance.delete()
    wait_for_power_state(vms_collection, instance.name, "terminated")


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
@pytest.mark.ignore_stream('5.11')
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
