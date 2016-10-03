import fauxfactory
import pytest
from cfme import test_requirements
from cfme.cloud.keypairs import KeyPair
from utils import testgen
from utils.version import current_version
from utils.providers import setup_a_provider as _setup_a_provider

pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() > '5.7', test_requirements.provision)
]

pytestmark = [pytest.mark.usefixtures("setup_a_provider")]


@pytest.fixture(scope="module")
def setup_a_provider():
    _setup_a_provider(prov_class="cloud", prov_type="openstack", validate=True, check_existing=True)


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['openstack'])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope='module')


@pytest.mark.tier(3)
def test_keypair_crud():
    """ This will test whether it will create new Keypair and then deletes it.

    Prerequisites:
        * Cloud Provider must be added

    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Also delete it.
    """
    keypair = KeyPair(name=fauxfactory.gen_alphanumeric())
    keypair.create()
    keypair.delete()


def test_edit_tags(tag):
    """ This will test whether it will assign tags and remove the tags.

    Prerequisites:
        * Keypair must be added

    Steps:
        * Provide Keypair name.
        * Select the Keypair and assign the tags.
        * Also delete the tag which is assign in previous step.
    """
    tag = ('Department', 'Accounting')
    keypair = KeyPair(name=fauxfactory.gen_alphanumeric())
    keypair.create()
    keypair.add_tag(tag)
    keypair.remove_tag(tag)
    keypair.delete()
