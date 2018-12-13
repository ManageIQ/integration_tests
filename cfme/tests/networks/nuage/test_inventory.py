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
