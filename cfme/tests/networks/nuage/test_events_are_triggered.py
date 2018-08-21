# -*- coding: utf-8 -*-
"""This module tests Nuage EMS events."""
import pytest

from wrapanapi.utils.random import random_name

from cfme.networks.provider.nuage import NuageProvider
from cfme.utils.log import logger


pytestmark = [
    pytest.mark.provider([NuageProvider])
]


@pytest.fixture
def with_nuage_sandbox(networks_provider):
    nuage = networks_provider.mgmt
    sandbox = box = {}

    # Create empty enterprise aka 'sandbox'.
    enterprise = box['enterprise'] = nuage.create_enterprise()
    logger.info('Created sandbox enterprise {} ({})'.format(enterprise.name, enterprise.id))

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

    # Let integration test do whatever it needs to do.
    yield sandbox

    # Destroy the sandbox.
    nuage.delete_enterprise(enterprise)
    logger.info('Destroyed sandbox enterprise {} ({})'.format(enterprise.name, enterprise.id))


def test_creating_entities_emits_events(register_event, with_nuage_sandbox):
    """
    Tests whether EMS events are emitted by Nuage server and recieved by MIQ. Here we test events
    that should be triggered upon entity creation. For example, when a new subnet is created on
    Nuage server, event of type 'nuage_subnet_create' should be emitted.

    Prerequisities:
        * A network provider that is set up and listening to events.

    Steps:
        * Deploy some entities outside of MIQ (directly in the provider)
        * Verify that expected events were captured by MIQ

    Important: register_event fixture must be listed before with_nuage_sandbox fixture because we
        need to start collecting events before we actually create the entities.
    """
    listener = register_event
    sandbox = with_nuage_sandbox

    expect_event(listener, 'nuage_enterprise_create', sandbox['enterprise'].id)
    expect_event(listener, 'nuage_domaintemplate_create', sandbox['template'].id)
    expect_event(listener, 'nuage_domain_create', sandbox['domain'].id)
    expect_event(listener, 'nuage_zone_create', sandbox['zone'].id)
    expect_event(listener, 'nuage_subnet_create', sandbox['subnet'].id)
    expect_event(listener, 'nuage_vport_create', sandbox['cont_vport'].id, comment='L3 cont')
    expect_event(listener, 'nuage_vport_create', sandbox['vm_vport'].id, comment='L3 vm')
    expect_event(listener, 'nuage_l2domaintemplate_create', sandbox['l2_template'].id)
    expect_event(listener, 'nuage_l2domain_create', sandbox['l2_domain'].id)
    expect_event(listener, 'nuage_vport_create', sandbox['l2_cont_vport'].id, comment='L2 cont')
    expect_event(listener, 'nuage_vport_create', sandbox['l2_vm_vport'].id, comment='L2 vm')
    expect_event(listener, 'nuage_policygroup_create', sandbox['group'].id, comment='L1')
    expect_event(listener, 'nuage_policygroup_create', sandbox['l2_group'].id, comment='L2')


def expect_event(listener, event_type, entity_id, comment=''):
    """
    Raise error unless event of type event_type is found with matching entity_id.

    Args:
        listener: instance of RestEventListener
        event_type: expected event type, e.g. 'nuage_subnet_create'
        entity_id: expected entity id, e.g. '184c55c9-5857-4404-bdcb-1ed99ec777eb'
        comment: comment that will be displayed if event was not emitted (optional)

    Returns: None
    """
    def cmp_function(_, full_data):
        # Nuage returns entities as a list, but there is always exactly one in there.
        return full_data['entities'][0]['ID'] == entity_id

    listener(
        {
            'full_data': '{} [ID={}] {}'.format(event_type, entity_id, comment),
            'cmp_func': cmp_function
        },
        source='NUAGE',
        event_type=event_type,
        first_event=True
    )
