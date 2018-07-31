# -*- coding: utf-8 -*-
"""This module tests Nuage EMS events."""
import pytest
import re
from argparse import Namespace
from contextlib import contextmanager

from wrapanapi.utils.random import random_name

from cfme.exceptions import NeedleNotFoundInLog
from cfme.networks.provider.nuage import NuageProvider
from cfme.utils.log import logger
from cfme.utils.wait import wait_for, TimedOutError

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


@pytest.fixture
def targeted_refresh(merkyl_setup, merkyl_inspector):
    """
    This fixture tests whether targeted refresh was triggered for given targets.
    It basically tails evm.log to see whether a line like this has occured:

    ```
    [Collection of targets with id: [{:ems_ref=>"b35d3afe-6f19-4da8-b1ee-b79de433cace"}, ... ]]
    ```
    for each target and raises an error if not.

    Usage:

        def test_something(targeted_refresh)
                trigger_targeted_refresh() <- some function that will trigger
                                              targeted refresh
                with targeted_refresh.target_timeout():
                    targeted_refresh.register_target('ref-123456', 'Subnet named TEST')
                    targeted_refresh.register_target('ref-aaaabb', 'Router named TEST')
    """
    evm_log = '/var/www/miq/vmdb/log/evm.log'
    needle_template = r'^.*Collection of targets with id.*:ems_ref=>"{}".*$'
    merkyl_inspector.add_log(evm_log)
    merkyl_inspector.reset_log(evm_log)
    targets = set()  # { (ems_ref, comment), (ems_ref, comment), ... }

    def check_log():
        logger.info('Looking for %s needles in evm.log: %s', len(targets), [t[1] for t in targets])
        content = merkyl_inspector.get_log(evm_log)
        for target in set(targets):
            if target[0].search(content):
                logger.info('Found needle %s', target[1])
                targets.remove(target)
        return len(targets) == 0

    @contextmanager
    def timeout():
        yield

        try:
            wait_for(check_log, delay=5, num_sec=60)
        except TimedOutError:
            raise NeedleNotFoundInLog('Targeted refresh did not trigger for:\n{}'.format(
                                      ',\n'.join(map(lambda t: '- ' + t[1], targets))))

    def register_target(ems_ref, comment):
        targets.add((re.compile(needle_template.format(ems_ref), re.MULTILINE), comment))

    yield Namespace(register_target=register_target, timeout=timeout)


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


def test_creating_entities_triggers_targeted_refresh(targeted_refresh, with_nuage_sandbox):
    """
    Test whether targeted refresh is triggered when entities are created. This way
    we check whether Automation Instances are properly set to trigger targeted refresh
    when event comes.

    config:
        Before running this test you have to configure merkyl (see how in
        cfme/fixtures/merkyl.py) and make sure you have port 8192 opened
        on your appliance.

    Steps:
        * Deploy entities outside of CFME (directly in the provider)
        * Verify that targeted refreshes where triggered

    Important: targeted_refresh fixture must be listed before with_nuage_sandbox
    fixture because we have to start tracking evm.log before we create the entites
    """
    sandbox = with_nuage_sandbox
    with targeted_refresh.timeout():
        targeted_refresh.register_target(sandbox['enterprise'].id, 'Enterprise')
        targeted_refresh.register_target(sandbox['domain'].id, 'Domain')
        targeted_refresh.register_target(sandbox['subnet'].id, 'Subnet')
        targeted_refresh.register_target(sandbox['cont_vport'].id, 'Container vPort (L3)')
        targeted_refresh.register_target(sandbox['vm_vport'].id, 'VM vPort (L3)')
        targeted_refresh.register_target(sandbox['l2_domain'].id, 'Domain (L2)')
        targeted_refresh.register_target(sandbox['l2_cont_vport'].id, 'Container vPort (L2)')
        targeted_refresh.register_target(sandbox['l2_vm_vport'].id, 'VM vPort (L2)')
        targeted_refresh.register_target(sandbox['group'].id, 'Security group (L3)')
        targeted_refresh.register_target(sandbox['l2_group'].id, 'Security group (L2)')


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
