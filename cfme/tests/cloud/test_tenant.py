# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.cloud.tenant import Tenant
from utils import testgen
from utils.log import logger
from utils.version import current_version


pytest_generate_tests = testgen.generate([OpenStackProvider], scope='module')

# Tag requirements here, does not currently match any requirements categories


def _refresh_provider(provider):
    provider.load_details()
    provider.refresh_provider_relationships()


@pytest.yield_fixture(scope='function')
def tenant(provider, setup_provider):
    tenant = Tenant(name=fauxfactory.gen_alphanumeric(8), provider=provider)

    yield tenant

    try:
        tenant.delete()
    except Exception:
        logger.warning('Exception while attempting to delete tenant fixture, continuing')
        pass


@pytest.mark.uncollectif(lambda: current_version() < '5.7')
def test_tenant_crud(tenant):
    """ Tests tenant create and delete

    Metadata:
        test_flag: tenant
    """

    tenant.create(cancel=True)
    assert not tenant.exists()

    tenant.create()
    # # requires provider after each tenant CRUD
    assert tenant.exists()

    tenant.update({'name': 'new_name'})
    # requires provider after each tenant CRUD
    _refresh_provider(tenant.provider)
    assert tenant.exists()

    tenant.delete(from_details=False, cancel=True)
    # requires provider after each tenant CRUD
    _refresh_provider(tenant.provider)
    assert tenant.exists()

    tenant.delete(from_details=True, cancel=False)
    # requires provider after each tenant CRUD
    _refresh_provider(tenant.provider)
    assert not tenant.exists()
