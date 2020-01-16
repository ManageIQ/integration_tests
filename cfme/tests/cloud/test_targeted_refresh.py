import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.utils.blockers import BZ
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

DELAY = 15
TIMEOUT = 1500


def wait_for_power_state(vms_collection, instance_name, power_state):
    wait_for(lambda: vms_collection.get(name=instance_name)["power_state"] == power_state, delay=15,
             timeout=TIMEOUT, handle_exception=True)


def wait_for_deleted(collection, entity_name):
    wait_for(lambda: all([False if e.name == entity_name else True for e in collection.all]),
             delay=15, timeout=TIMEOUT, handle_exception=True)


def cleanup_if_exists(entity):
    try:
        if entity.exists:
            return entity.cleanup()
    except Exception:
        return True


def test_targeted_refresh_instance(appliance, provider, request):
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
    if not instance:
        pytest.fail("Instance wasn't successfully created using API!")
    request.addfinalizer(lambda: cleanup_if_exists(instance))

    # running
    wait_for_power_state(vms_collection, instance.name, "on")

    # stopped
    instance.stop()
    wait_for_power_state(vms_collection, instance.name, "off")

    # update
    instance.rename(random_vm_name('refr'))
    instance.change_type('t1.small')
    wait_for(lambda: flavors_collection.get(id=vms_collection.get(name=instance.name)["flavor_id"])
        ["name"] == instance.type, delay=15, timeout=TIMEOUT, handle_exception=True)

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


def test_targeted_refresh_network(appliance, provider, request):
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
    # create
    network = provider.mgmt.create_network()
    if not network:
        pytest.fail("Network wasn't successfully created using API!")
    request.addfinalizer(lambda: cleanup_if_exists(network))
    network_collection = appliance.rest_api.collections.cloud_networks
    wait_for(lambda: network_collection.get(ems_ref=network.uuid), delay=15, timeout=TIMEOUT,
             handle_exception=True)

    # update - change name
    new_name = fauxfactory.gen_alpha()
    network.rename(new_name)
    wait_for(lambda: network_collection.get(name=new_name), delay=15, timeout=TIMEOUT,
             handle_exception=True)

    # delete
    network.delete()
    wait_for_deleted(network_collection, new_name)


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


def test_targeted_refresh_volume(appliance, provider, request):
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
            3. Volume ATTACH
            4. Volume DETACH
            5. Volume DELETE
    """
    template_id = provider.mgmt.get_template(
        provider.data.templates.get('small_template').name).uuid
    instance = provider.mgmt.create_vm(template_id, vm_name=random_vm_name('refr'))
    if not instance:
        pytest.fail("Instance wasn't successfully created using API!")
    request.addfinalizer(lambda: cleanup_if_exists(instance))

    volume_name = fauxfactory.gen_alpha()
    volume_collection = appliance.rest_api.collections.cloud_volumes
    # create
    volume = provider.mgmt.create_volume(instance.az, name=volume_name)
    if not volume:
        pytest.fail("Volume wasn't successfully created using API!")
    request.addfinalizer(lambda: cleanup_if_exists(volume))
    wait_for(lambda: volume_collection.get(name=volume_name), delay=15, timeout=TIMEOUT,
             handle_exception=True)
    # update name
    new_volume_name = fauxfactory.gen_alpha()
    volume.rename(new_volume_name)
    wait_for(lambda: volume_collection.get(name=new_volume_name), delay=15, timeout=TIMEOUT,
             handle_exception=True)
    # update size
    if not BZ(1754874, forced_streams=["5.10", "5.11"]).blocks:
        new_size = 20
        volume.resize(new_size)
        wait_for(lambda: volume_collection.get(name=new_volume_name).size ==
                (new_size * 1024 * 1024 * 1024), delay=15, timeout=TIMEOUT, handle_exception=True)
    # attach
    volume.attach(instance.uuid)
    wait_for(lambda: volume_collection.get(name=new_volume_name), delay=15, timeout=TIMEOUT,
             handle_exception=True)
    # detach
    volume.detach(instance.uuid)
    wait_for(lambda: volume_collection.get(name=new_volume_name), delay=15, timeout=TIMEOUT,
             handle_exception=True)
    # delete
    wait_for(lambda: volume.cleanup(), delay=15, timeout=TIMEOUT, handle_exception=True)
    wait_for_deleted(volume_collection, new_volume_name)


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


@pytest.mark.manual
def test_targeted_refresh_template():
    """
    AWS naming is AMI
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: high
        initialEstimate: 2/3h
        startsin: 5.9
        testSteps:
            1. Template CREATE
            2. Template UPDATE
            3. Template DELETE
    """
    pass
