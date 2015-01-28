import pytest

from cfme.cloud.tenant import Tenant
from utils import testgen
from utils.randomness import generate_random_string

pytest_generate_tests = testgen.generate(testgen.provider_by_type, ['openstack'],
                                         scope='module')


@pytest.fixture
def tenant(provider_key):
    return Tenant(name=generate_random_string(size=8),
                  description=generate_random_string(size=8),
                  provider_key=provider_key)


def test_tenant(provider_mgmt, tenant, provider_key):
    """ Tests tenant (currently disabled)

    Metadata:
        test_flag: tenant
    """
    print tenant.name, tenant.description, provider_key
