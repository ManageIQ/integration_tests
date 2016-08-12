# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import fauxfactory
import pytest

from cfme.cloud.tenant import Tenant
from utils import testgen

pytest_generate_tests = testgen.generate(testgen.provider_by_type, ['openstack'],
                                         scope='module')


@pytest.fixture
def tenant(provider):
    return Tenant(name=fauxfactory.gen_alphanumeric(8),
                  description=fauxfactory.gen_alphanumeric(8),
                  provider_key=provider.key)


@pytest.mark.uncollect()
def test_tenant(tenant, provider):
    """ Tests tenant (currently disabled)

    Metadata:
        test_flag: tenant
    """
    pass
