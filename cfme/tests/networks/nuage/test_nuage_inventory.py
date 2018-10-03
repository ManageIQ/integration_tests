# -*- coding: utf-8 -*-
import pytest
from netaddr import IPAddress

from cfme.networks.provider.nuage import NuageProvider
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [pytest.mark.provider([NuageProvider], scope="module")]


def test_subnet_details_stats(provider, with_nuage_sandbox):
    """
    This test creates Nuage enterprise and its entities, including subnet.
    Then it validates inventory of created subnet.

    Steps:
        * Deploy some entities outside of MIQ (directly in the provider)
        * Create dictionary with stats that will be validated
        * Find created subnet in database and validate its stats
    """
    sandbox = with_nuage_sandbox
    cidr = '{address}/{netmask}'.format(
        address=sandbox['subnet'].address,
        netmask=IPAddress(sandbox['subnet'].netmask).netmask_bits()
    )
    domain = sandbox['subnet'].parent_object.parent_object
    subnet_stats = {
        'name_value': sandbox['subnet'].name,
        'type_value': 'ManageIQ/Providers/Nuage/Network Manager/Cloud Subnet/L3',
        'cidr_value': cidr,
        'gateway_value': sandbox['subnet'].gateway,
        'network_protocol_value': sandbox['subnet'].ip_type.lower(),
        'network_manager_value': provider.name,
        'cloud_tenant_value': domain.parent_object.name,
        'network_router_value': domain.name,
        'network_ports_num': len(sandbox['subnet'].vports),
        'security_groups_num': sum(len(port.policy_groups) for port in sandbox['subnet'].vports),
    }
    provider.refresh_provider_relationships()
    subnet = object_in_vmdb_with_timeout('nuage_network_subnets', provider, sandbox['subnet'].id)
    subnet.validate_stats(subnet_stats)


def test_cloud_tenant_details_stats(provider, with_nuage_sandbox):
    """
    This test creates Nuage enterprise (cloud tenant) and its entities.
    Then it validates inventory of created tenant.

    Steps:
        * Deploy some entities outside of MIQ (directly in the provider)
        * Create dictionary with stats that will be validated
        * Find created subnet in database and validate its stats
    """
    sandbox = with_nuage_sandbox
    subnets = []
    [subnets.extend(z.subnets) for d in sandbox['enterprise'].domains for z in d.zones]
    l2_groups = sum([len(d.policy_groups) for d in sandbox['enterprise'].l2_domains])
    groups = sum([len(d.policy_groups) for d in sandbox['enterprise'].domains])
    vports = sum([len(s.vports) for s in subnets])
    l2_vports = sum([len(d.vports) for d in sandbox['enterprise'].l2_domains])
    tenant_stats = {
        'name_value': sandbox['enterprise'].name,
        'network_manager_value': provider.name,
        'cloud_subnets_num': len(subnets) + len(sandbox['enterprise'].l2_domains),
        'network_routers_num': len(sandbox['enterprise'].domains),
        'security_groups_num': l2_groups + groups,
        'floating_ips_num': sum([len(d.floating_ips) for d in sandbox['enterprise'].domains]),
        'network_ports_num': vports + l2_vports,
    }
    provider.refresh_provider_relationships()
    tenant = object_in_vmdb_with_timeout(
        'nuage_network_tenants', provider, sandbox['enterprise'].id)
    tenant.validate_stats(tenant_stats)


def object_in_vmdb_with_timeout(table, provider, ems_ref):

    def object_from_vmdb():
        logger.info('Looking for {table} with ems_ref {ems_ref} in the VMDB...'.format(
            table=table, ems_ref=ems_ref))
        return getattr(provider.appliance.collections, table).find_by_ems_ref(ems_ref, provider)

    obj, _ = wait_for(
        object_from_vmdb,
        num_sec=60,
        delay=5,
        fail_condition=None
    )
    return obj
