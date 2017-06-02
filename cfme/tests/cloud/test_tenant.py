import fauxfactory
import pytest
from cfme.cloud.provider.openstack import OpenStackProvider
from utils.update import update
from cfme.cloud.tenant import Tenant
from utils import testgen
from utils.log import logger
from utils.version import current_version


pytest_generate_tests = testgen.generate([OpenStackProvider], scope='module')


@pytest.yield_fixture(scope='function')
def tenant(provider, setup_provider):
    tenant = Tenant(name=fauxfactory.gen_alphanumeric(8), provider=provider)

    yield tenant

    try:
        if tenant.exists():
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

    tenant.create(cancel=True)
    assert not tenant.exists()

    tenant.create()

    tenant.wait_for_appear()
    assert tenant.exists()
    with update(tenant):
        tenant.name = fauxfactory.gen_alphanumeric(8)
    assert tenant.exists()

    tenant.delete(from_details=False, cancel=True)
    assert tenant.exists()

    tenant.delete(from_details=True, cancel=False)
    # BZ#1411112 Delete/update cloud tenant
    #  not reflected in UI in cloud tenant list
    tenant.provider.refresh_provider_relationships()
    assert not tenant.exists()
