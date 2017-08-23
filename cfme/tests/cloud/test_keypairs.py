import fauxfactory
import pytest
from Crypto.PublicKey import RSA

from cfme.cloud.keypairs import KeyPair
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.exceptions import KeyPairNotFound
from cfme.web_ui import mixins
from cfme.utils import testgen
from cfme.utils.blockers import BZ
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import TimedOutError

pytestmark = [
    pytest.mark.usefixtures('setup_provider', 'openstack_provider')
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [OpenStackProvider])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope='module')


@pytest.mark.tier(3)
def test_keypair_crud(openstack_provider):
    """ This will test whether it will create new Keypair and then deletes it.
    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Also delete it.
    """
    keypair = KeyPair(name=fauxfactory.gen_alphanumeric(), provider=openstack_provider)
    try:
        keypair.create()
    except TimedOutError:
        if BZ(1444520, forced_streams=['5.6', '5.7', 'upstream']).blocks:
            pytest.skip('Timed out creating keypair, BZ1444520')
        else:
            pytest.fail('Timed out creating keypair')
    assert keypair.exists

    try:
        keypair.delete(wait=True)
    except TimedOutError:
        openstack_provider.mgmt.api.keypairs.delete(keypair.name)
        pytest.fail('Timed out deleting keypair')

    with pytest.raises(KeyPairNotFound):
        navigate_to(keypair, 'Details')


@pytest.mark.tier(3)
def test_keypair_crud_with_key(openstack_provider):
    """ This will test whether it will create new Keypair and then deletes it.

    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Also delete it.
    """
    key = RSA.generate(1024)
    public_key = key.publickey().exportKey('OpenSSH')
    keypair = KeyPair(name=fauxfactory.gen_alphanumeric(),
                      public_key=public_key,
                      provider=openstack_provider)
    try:
        keypair.create()
    except TimedOutError:
        if BZ(1444520, forced_streams=['5.6', '5.7', 'upstream']).blocks:
            pytest.skip('Timed out creating keypair, BZ1444520')
        else:
            pytest.fail('Timed out creating keypair')
    assert keypair.exists

    try:
        keypair.delete(wait=True)
    except TimedOutError:
        openstack_provider.mgmt.api.keypairs.delete(keypair.name)
        pytest.fail('Timed out deleting keypair')

    with pytest.raises(KeyPairNotFound):
        navigate_to(keypair, 'Details')


@pytest.mark.tier(3)
def test_keypair_create_cancel(openstack_provider):
    """ This will test cancelling on adding a keypair

    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Also delete it.
    """
    keypair = KeyPair(name=fauxfactory.gen_alphanumeric(), provider=openstack_provider)
    keypair.create(cancel=True)

    with pytest.raises(KeyPairNotFound):
        navigate_to(keypair, 'Details')


def test_keypair_add_and_remove_tag(openstack_provider):
    """ This will test whether it will add and remove tag for newly created Keypair or not
    and then deletes it.

    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Add tag to Keypair.
        * Remove tag from Keypair
        * Also delete it.
    """
    tag = ('Department', 'Accounting')
    keypair = KeyPair(name=fauxfactory.gen_alphanumeric(), provider=openstack_provider)
    try:
        keypair.create()
    except TimedOutError:
        if BZ(1444520, forced_streams=['5.6', '5.7', 'upstream']).blocks:
            pytest.skip('Timed out creating keypair, BZ1444520')
        else:
            pytest.fail('Timed out creating keypair')
    assert keypair.exists

    keypair.add_tag(tag)
    tagged_value = mixins.get_tags(tag="My Company Tags")
    assert tuple(tagged_value[0].split(": ", 1)) == tag, "Add tag failed."

    keypair.remove_tag(tag)
    tagged_value1 = mixins.get_tags(tag="My Company Tags")
    assert tagged_value1 != tagged_value, "Remove tag failed."
    # Above small conversion in assert statement convert 'tagged_value' in tuple("a","b") and then
    # compare with tag which is tuple. As get_tags will return assigned tag in list format["a: b"].

    try:
        keypair.delete(wait=True)
    except TimedOutError:
        openstack_provider.mgmt.api.keypairs.delete(keypair.name)
        pytest.fail('Timed out deleting keypair')

    with pytest.raises(KeyPairNotFound):
        navigate_to(keypair, 'Details')
