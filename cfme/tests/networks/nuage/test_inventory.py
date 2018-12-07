import pytest

from cfme.networks.provider.nuage import NuageProvider

pytestmark = [
    pytest.mark.provider([NuageProvider], scope='module')
]


def test_tenant_details(setup_provider_modscope, provider, with_nuage_sandbox_modscope):
    sandbox = with_nuage_sandbox_modscope
    tenant_name = sandbox['enterprise'].name
    tenant = provider.collections.cloud_tenants.instantiate(name=tenant_name, provider=provider)

    tenant.validate_stats({
        ('relationships', 'Cloud Subnets'): '2',
        ('relationships', 'Network Routers'): '1',
        ('relationships', 'Security Groups'): '2',
        ('relationships', 'Network Ports'): '4'
    })


def test_subnet_details(setup_provider_modscope, provider, with_nuage_sandbox_modscope):
    """
    Ensure L3 subnet details displays expected info.

    L3 subnets are always connected to routers, hence we navigate to them as
      Tenant > Router > Subnet
    """
    sandbox = with_nuage_sandbox_modscope
    tenant_name = sandbox['enterprise'].name
    subnet_name = sandbox['subnet'].name
    router_name = sandbox['domain'].name
    tenant = provider.collections.cloud_tenants.instantiate(name=tenant_name, provider=provider)
    router = tenant.collections.routers.instantiate(name=router_name)
    subnet = router.collections.subnets.instantiate(name=subnet_name)

    subnet.validate_stats({
        ('properties', 'Name'): subnet_name,
        ('properties', 'Type'): 'ManageIQ/Providers/Nuage/Network Manager/Cloud Subnet/L3',
        ('properties', 'CIDR'): '192.168.0.0/24',
        ('properties', 'Gateway'): '192.168.0.1',
        ('properties', 'Network protocol'): 'ipv4',
        ('relationships', 'Network Router'): router_name,
        ('relationships', 'Network Ports'): '2',
        ('relationships', 'Security Groups'): '0',
    })


def test_l2_subnet_details(setup_provider_modscope, provider, with_nuage_sandbox_modscope):
    """
    Ensure L2 subnet details displays expected info.

    L2 subnets act as standalone and are thus not connected to any router.
    We navigate to them as
      Tenant > Subnet
    """
    sandbox = with_nuage_sandbox_modscope
    tenant_name = sandbox['enterprise'].name
    subnet_name = sandbox['l2_domain'].name
    tenant = provider.collections.cloud_tenants.instantiate(name=tenant_name, provider=provider)
    subnet = tenant.collections.subnets.instantiate(name=subnet_name)

    subnet.validate_stats({
        ('properties', 'Name'): subnet_name,
        ('properties', 'Type'): 'ManageIQ/Providers/Nuage/Network Manager/Cloud Subnet/L2',
        ('relationships', 'Network Ports'): '2',
        ('relationships', 'Security Groups'): '1',
    })


def test_network_router_details(setup_provider_modscope, provider, with_nuage_sandbox_modscope):
    sandbox = with_nuage_sandbox_modscope
    tenant_name = sandbox['enterprise'].name
    router_name = sandbox['domain'].name
    tenant = provider.collections.cloud_tenants.instantiate(name=tenant_name, provider=provider)
    router = tenant.collections.routers.instantiate(name=router_name)

    router.validate_stats({
        ('properties', 'Name'): router_name,
        ('properties', 'Type'): 'ManageIQ/Providers/Nuage/Network Manager/Network Router',
        ('relationships', 'Cloud Subnets'): '1',
        ('relationships', 'Security Groups'): '1',
    })
