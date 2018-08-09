# -*- coding: utf-8 -*-
"""This module tests events that are invoked by Network entities (e.g. subnets)."""
import pytest

from cfme.networks.provider.nuage import NuageProvider, NetworkProvider


pytestmark = [
    pytest.mark.provider([NetworkProvider])
]


@pytest.yield_fixture
def prerequisites(provider):
    provider.teardown_test_entities_on_provider()
    yield
    provider.teardown_test_entities_on_provider()


def test_events_create_entities(appliance, request, provider, register_event, networks_provider,
                                prerequisites):
    """
    Test whether events are emitted when default entities are created.

    Prerequisities:
        * A network provider that is set up and listening to events.

    Steps:
        * Deploy default entities outside of CFME (directly in the provider)
        * Verify that expected events were captured by CFME

    Metadata:
        test_flag: events
    """

    if provider.one_of(NuageProvider):
        register_event(
            nuage_entity_name_attr('enterprise', provider.mgmt.enterprise_name),
            source=provider.type.upper(),
            event_type='nuage_enterprise_create'
        )
        register_event(
            nuage_entity_name_attr('domaintemplate', provider.mgmt.domain_template_name),
            source=provider.type.upper(),
            event_type='nuage_domaintemplate_create'
        )
        register_event(
            nuage_entity_name_attr('domain', provider.mgmt.domain_name),
            source=provider.type.upper(),
            event_type='nuage_domain_create'
        )
        register_event(
            nuage_entity_name_attr('zone', provider.mgmt.zone_name),
            source=provider.type.upper(),
            event_type='nuage_zone_create'
        )
        register_event(
            nuage_entity_name_attr('subnet', provider.mgmt.subnet_name),
            source=provider.type.upper(),
            event_type='nuage_subnet_create'
        )

    provider.setup_test_entities_on_provider()


def nuage_entity_name_attr(type, name):
    """
    Construct event attribute that checks full_data for specific entity type and name.

    Args:
        type: expected entity type
        name: expected entity name

    Returns: a hash representing event attribute with given expecteions
    """
    def cmp_function(_, full_data):
        return (full_data['entityType'] == type and
            full_data['entities'][0]['name'] == name)
    return {'full_data': 'will be ignored', 'cmp_func': cmp_function}
