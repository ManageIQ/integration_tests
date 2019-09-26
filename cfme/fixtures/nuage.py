import pytest
from wrapanapi.utils.random import random_name

from cfme.utils.log import logger


def create_basic_sandbox(nuage):
    box = {}

    # Create empty enterprise aka 'sandbox'.
    enterprise = box['enterprise'] = nuage.create_enterprise()
    logger.info('Created sandbox enterprise %s (%s)', enterprise.name, enterprise.id)

    # Fill the sandbox with some entities.
    # Method `create_child` returns a tuple (object, connection) and we only need object.
    box['template'] = enterprise.create_child(
        nuage.vspk.NUDomainTemplate(name=random_name()))[0]
    box['domain'] = enterprise.create_child(
        nuage.vspk.NUDomain(name=random_name(), template_id=box['template'].id))[0]
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
        nuage.vspk.NUVPort(name=random_name(), type='VM'))[0]
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

    return box


@pytest.fixture
def with_nuage_sandbox(networks_provider):
    nuage = networks_provider.mgmt
    sandbox = create_basic_sandbox(nuage)

    # Let integration test do whatever it needs to do.
    yield sandbox

    # Destroy the sandbox.
    enterprise = sandbox['enterprise']
    nuage.delete_enterprise(enterprise)
    logger.info('Destroyed sandbox enterprise %s (%s)', enterprise.name, enterprise.id)


@pytest.fixture(scope='module')
def with_nuage_sandbox_modscope(appliance, setup_provider_modscope, provider):
    nuage = provider.mgmt
    sandbox = create_basic_sandbox(nuage)
    enterprise = sandbox['enterprise']
    logger.info('Performing a full refresh, so sandbox %s appears in the database', enterprise.name)
    provider.refresh_provider_relationships_and_wait(delay=10, refresh_delta=5)

    # Check if tenant exists in database, if not fail test immediately
    tenants_table = appliance.db.client['cloud_tenants']
    tenant = (appliance.db.client.session
              .query(tenants_table.name, tenants_table.ems_ref)
              .filter(tenants_table.ems_ref == enterprise.id).first())
    assert tenant is not None, 'Nuage sandbox tenant inventory missing: {}'.format(enterprise.name)

    # Let integration test do whatever it needs to do.
    yield sandbox

    # Destroy the sandbox.
    nuage.delete_enterprise(enterprise)
    logger.info('Destroyed sandbox enterprise %s (%s)', enterprise.name, enterprise.id)
