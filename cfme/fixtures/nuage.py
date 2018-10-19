import pytest
import random

from wrapanapi.utils.random import random_name

from cfme.utils.log import logger


@pytest.fixture
def with_nuage_sandbox(networks_provider):
    nuage = networks_provider.mgmt
    sandbox = box = {}

    # Create empty enterprise aka 'sandbox'.
    enterprise = box['enterprise'] = nuage.create_enterprise()
    logger.info('Created sandbox enterprise {} ({})'.format(enterprise.name, enterprise.id))

    # Create shared network resource
    box['shared_network'] = nuage.api.create_child(nuage.vspk.NUSharedNetworkResource(
        name=random_name(),
        address='11.12.13.{address}'.format(address=random.randint(0, 63) * 4),
        netmask='255.255.255.252',
        type='FLOATING'
    ))[0]

    # Fill the sandbox with some entities.
    # Method `create_child` returns a tuple (object, connection) and we only need object.
    box['template'] = enterprise.create_child(
        nuage.vspk.NUDomainTemplate(name=random_name()))[0]
    box['domain'] = enterprise.create_child(
        nuage.vspk.NUDomain(name=random_name(), template_id=box['template'].id))[0]
    box['floating_ip'] = box['domain'].create_child(nuage.vspk.NUFloatingIp(
        associated_shared_network_resource_id=box['shared_network'].id
    ))[0]
    box['zone'] = box['domain'].create_child(
        nuage.vspk.NUZone(name=random_name()))[0]
    box['subnet'] = box['zone'].create_child(
        nuage.vspk.NUSubnet(
            name=random_name(),
            address='192.168.0.0',
            netmask='255.255.255.0',
            gateway='192.168.0.1'))[0]
    box['cont_vport'] = box['subnet'].create_child(
        nuage.vspk.NUVPort(name=random_name(), type='CONTAINER'))[0]
    box['vm_vport'] = box['subnet'].create_child(
        nuage.vspk.NUVPort(
            name=random_name(),
            type='VM',
            associated_floating_ip_id=box['floating_ip'].id
        ))[0]
    box['l2_template'] = enterprise.create_child(
        nuage.vspk.NUL2DomainTemplate(name=random_name()))[0]
    box['l2_domain'] = enterprise.create_child(
        nuage.vspk.NUL2Domain(name=random_name(), template_id=box['l2_template'].id))[0]
    box['l2_cont_vport'] = box['l2_domain'].create_child(
        nuage.vspk.NUVPort(name=random_name(), type='CONTAINER'))[0]
    box['l2_vm_vport'] = box['l2_domain'].create_child(
        nuage.vspk.NUVPort(name=random_name(), type='VM'))[0]
    box['group'] = box['domain'].create_child(
        nuage.vspk.NUPolicyGroup(name=random_name()))[0]
    box['l2_group'] = box['l2_domain'].create_child(
        nuage.vspk.NUPolicyGroup(name=random_name()))[0]

    # Let integration test do whatever it needs to do.
    yield sandbox

    # Destroy the sandbox.
    nuage.delete_enterprise(enterprise)
    box['shared_network'].delete()
    logger.info('Destroyed sandbox enterprise {} ({})'.format(enterprise.name, enterprise.id))
