import fauxfactory
import pytest
from cfme.cloud.keypairs import KeyPair
from utils import testgen
from utils.version import current_version
from utils.providers import setup_a_provider as _setup_a_provider

pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() > '5.7')
]


@pytest.fixture(scope="module")
def a_provider():
    return _setup_a_provider(
        prov_class="cloud", prov_type="openstack", validate=True, check_existing=True)


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['openstack'])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope='module')


@pytest.mark.tier(3)
def test_keypair_crud(a_provider):
    """ This will test whether it will create new Keypair and then deletes it.

    Prerequisites:
        * Cloud Provider must be added

    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Also delete it.
    """
    keypair = KeyPair(name=fauxfactory.gen_alphanumeric(), provider=a_provider)
    keypair.create()
    keypair.delete()
