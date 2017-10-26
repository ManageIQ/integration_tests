import fauxfactory
import pytest
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.update import update
from cfme.cloud.tenant import TenantCollection
from cfme.utils.log import logger
from cfme.utils.version import current_version


pytestmark = [pytest.mark.provider([OpenStackProvider], scope='module')]


@pytest.yield_fixture(scope='function')
def tenant(provider, setup_provider, appliance):
    collection = appliance.collections.cloud_tenants
    tenant = collection.create(name=fauxfactory.gen_alphanumeric(8), provider=provider)

    yield tenant

    try:
        if tenant.exists:
            tenant.delete()

    except Exception:
        logger.warning(
            'Exception while attempting to delete tenant fixture, continuing')
    finally:
        if tenant.name in provider.mgmt.list_tenant():
            provider.mgmt.remove_tenant(tenant.name)


@pytest.mark.uncollectif(lambda: current_version() < '5.7')
def test_tenant_crud(tenant):
    """ Tests tenant create and delete

    Metadata:
        test_flag: tenant
    """

    with update(tenant):
        tenant.name = fauxfactory.gen_alphanumeric(8)
    tenant.wait_for_appear()
    assert tenant.exists
