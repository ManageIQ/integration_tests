import fauxfactory
import pytest
from cfme.cloud.keypairs import KeyPair
from cfme.cloud.provider.openstack import OpenStackProvider
from fixtures.provider import setup_one_by_class_or_skip
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() > '5.7')
]


@pytest.fixture(scope="module")
def rhos_provider(request):
    return setup_one_by_class_or_skip(request, OpenStackProvider)


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [OpenStackProvider])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope='module')


@pytest.mark.tier(3)
def test_keypair_crud(rhos_provider):
    """ This will test whether it will create new Keypair and then deletes it.

    Prerequisites:
        * Cloud Provider must be added

    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Also delete it.
    """
    keypair = KeyPair(name=fauxfactory.gen_alphanumeric(), provider=rhos_provider)
    keypair.create()
    keypair.delete()
