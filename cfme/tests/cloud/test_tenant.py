# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.cloud.tenant import Tenant
from utils import testgen

pytest_generate_tests = testgen.generate(testgen.provider_by_type, ['openstack'],
                                         scope='module')


@pytest.fixture
def tenant(provider_key):
    return Tenant(name=fauxfactory.gen_alphanumeric(8),
                  description=fauxfactory.gen_alphanumeric(8),
                  provider_key=provider_key)


def test_tenant(provider_mgmt, tenant, provider_key):
    """ Tests tenant (currently disabled)

    Metadata:
        test_flag: tenant
    """
    print tenant.name, tenant.description, provider_key
