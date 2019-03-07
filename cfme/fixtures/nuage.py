from argparse import Namespace

import pytest
from wrapanapi.utils.random import random_name

from cfme.utils.log import logger
from cfme.utils.wait import wait_for


def create_basic_sandbox(nuage):
    box = Namespace()

    # Create empty enterprise aka 'sandbox'.
    box.enterprise = get_object_dictionary(nuage.create_enterprise())
    logger.info('Created sandbox enterprise %s (%s)',
                box.enterprise['name'], box.enterprise['id'])

    # Fill the sandbox with some entities.
    # Method `create_child` returns a tuple (object, connection) and we only need object.
    box.template = get_object_dictionary(box.enterprise['obj'].create_child(
        nuage.vspk.NUDomainTemplate(name=random_name()))[0])
    box.domain = get_object_dictionary(box.enterprise['obj'].create_child(
        nuage.vspk.NUDomain(name=random_name(), template_id=box.template['obj'].id))[0])
    box.domain.update(num_subnets=1, num_security_groups=1)
    box.zone = get_object_dictionary(box.domain['obj'].create_child(
        nuage.vspk.NUZone(name=random_name()))[0])
    box.subnet = get_object_dictionary(box.zone['obj'].create_child(
        nuage.vspk.NUSubnet(
            name=random_name(),
            address='192.168.0.0',
            netmask='255.255.255.0',
            gateway='192.168.0.1'))[0])
    box.subnet.update(num_ports=2, num_security_groups=0)
    box.cont_vport = get_object_dictionary(box.subnet['obj'].create_child(
        nuage.vspk.NUVPort(name=random_name(), type='CONTAINER'))[0])
    box.cont_vport.update(num_subnets=1)
    box.vm_vport = get_object_dictionary(box.subnet['obj'].create_child(
        nuage.vspk.NUVPort(name=random_name(), type='VM'))[0])
    box.vm_vport.update(num_subnets=1)
    box.l2_template = get_object_dictionary(box.enterprise['obj'].create_child(
        nuage.vspk.NUL2DomainTemplate(name=random_name()))[0])
    box.l2_domain = get_object_dictionary(box.enterprise['obj'].create_child(
        nuage.vspk.NUL2Domain(name=random_name(), template_id=box.l2_template['obj'].id))[0])
    box.l2_domain.update(num_ports=2, num_security_groups=1)
    box.l2_cont_vport = get_object_dictionary(box.l2_domain['obj'].create_child(
        nuage.vspk.NUVPort(name=random_name(), type='CONTAINER'))[0])
    box.l2_cont_vport.update(num_subnets=1)
    box.l2_vm_vport = get_object_dictionary(box.l2_domain['obj'].create_child(
        nuage.vspk.NUVPort(name=random_name(), type='VM'))[0])
    box.l2_vm_vport.update(num_subnets=1)
    box.group = get_object_dictionary(box.domain['obj'].create_child(
        nuage.vspk.NUPolicyGroup(name=random_name()))[0])
    box.l2_group = get_object_dictionary(box.l2_domain['obj'].create_child(
        nuage.vspk.NUPolicyGroup(name=random_name()))[0])

    box.counts = {
        'num_subnets': 2,
        'num_network_routers': 1,
        'num_security_groups': 2,
        'num_network_ports': 4
    }
    return box


def get_object_dictionary(obj):
    return dict(obj=obj, name=obj.name, id=obj.id)


@pytest.fixture
def with_nuage_sandbox(networks_provider):
    nuage = networks_provider.mgmt
    sandbox = create_basic_sandbox(nuage)

    # Let integration test do whatever it needs to do.
    yield sandbox

    # Destroy the sandbox.
    enterprise = sandbox.enterprise['obj']
    nuage.delete_enterprise(enterprise)
    logger.info('Destroyed sandbox enterprise %s (%s)', enterprise.name, enterprise.id)


@pytest.fixture(scope='module')
def with_nuage_sandbox_modscope(appliance, setup_provider_modscope, provider):
    nuage = provider.mgmt
    sandbox = create_basic_sandbox(nuage)
    enterprise = sandbox.enterprise
    logger.info('Performing a full refresh, so sandbox %s appears in the database',
                enterprise['name'])
    provider.refresh_provider_relationships()
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=5), timeout=600, delay=10)

    # Check if tenant exists in database, if not fail test immediately
    tenants_table = appliance.db.client['cloud_tenants']
    tenant = (appliance.db.client.session
              .query(tenants_table.name, tenants_table.ems_ref)
              .filter(tenants_table.ems_ref == enterprise['id']).first())
    assert tenant is not None, 'Nuage sandbox tenant inventory missing: {}'.format(
        enterprise['name'])

    # Let integration test do whatever it needs to do.
    yield sandbox

    # Destroy the sandbox.
    nuage.delete_enterprise(enterprise['obj'])
    logger.info('Destroyed sandbox enterprise %s (%s)', enterprise['name'], enterprise['id'])
