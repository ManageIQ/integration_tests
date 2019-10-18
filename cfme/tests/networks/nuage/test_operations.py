import fauxfactory
import pytest

from cfme.networks.provider.nuage import NuageProvider
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.provider([NuageProvider])
]


def test_router_add_subnet(provider, with_nuage_sandbox):
    """
    Ensure that subnet is added on network router

    We navigate to router through Provider > Tenant > Network Router
    """
    sandbox = with_nuage_sandbox
    tenant_name = sandbox.enterprise['name']
    router_name = sandbox.domain['name']
    tenant = provider.collections.cloud_tenants.instantiate(name=tenant_name, provider=provider)
    router = tenant.collections.routers.instantiate(name=router_name)
    subnet_name = fauxfactory.gen_alphanumeric(length=7)
    router.add_subnet(subnet_name, '172.16.0.0', '255.255.0.0', '172.16.0.1')
    subnet = get_subnet_from_db_with_timeout(provider.appliance, subnet_name, router_name)

    assert subnet is not None


def get_subnet_from_db_with_timeout(appliance, subnet_name, router_name):
    def get_object():
        logger.info('Looking for Cloud Subnet with name %s in the VMDB...', subnet_name)
        subnets = appliance.db.client['cloud_subnets']
        network_routers = appliance.db.client['network_routers']
        return (appliance.db.client.session.query(subnets.name)
                .filter(subnets.name == subnet_name, network_routers.name == router_name).first())

    obj, _ = wait_for(get_object, num_sec=60, delay=5, fail_condition=None)
    return obj
