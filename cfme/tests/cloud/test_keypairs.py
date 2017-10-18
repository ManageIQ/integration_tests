import fauxfactory
import pytest
from Crypto.PublicKey import RSA

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.blockers import BZ
from cfme.utils.wait import TimedOutError

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([OpenStackProvider], scope="module")
]


@pytest.mark.tier(3)
def test_keypair_crud(appliance, provider):
    """ This will test whether it will create new Keypair and then deletes it.
    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Also delete it.
    """
    keypairs = appliance.collections.keypairs
    try:
        keypair = keypairs.create(name=fauxfactory.gen_alphanumeric(), provider=provider)
    except TimedOutError:
        if BZ(1444520, forced_streams=['5.6', '5.7', 'upstream']).blocks:
            pytest.skip('Timed out creating keypair, BZ1444520')
        else:
            pytest.fail('Timed out creating keypair')
    assert keypair.exists

    keypair.delete(wait=True)
    assert not keypair.exists


@pytest.mark.tier(3)
def test_keypair_crud_with_key(openstack_provider, keypairs):
    """ This will test whether it will create new Keypair and then deletes it.

    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Also delete it.
    """
    key = RSA.generate(1024)
    public_key = key.publickey().exportKey('OpenSSH')
    try:
        keypair = keypairs.create(fauxfactory.gen_alphanumeric(), openstack_provider, public_key)
    except TimedOutError:
        if BZ(1444520, forced_streams=['5.6', '5.7', 'upstream']).blocks:
            pytest.skip('Timed out creating keypair, BZ1444520')
        else:
            pytest.fail('Timed out creating keypair')
    assert keypair.exists

    keypair.delete(wait=True)
    assert not keypair.exists


@pytest.mark.tier(3)
def test_keypair_create_cancel(openstack_provider, keypairs):
    """ This will test cancelling on adding a keypair

    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Also delete it.
    """
    keypair = keypairs.create(name="", provider=openstack_provider, cancel=True)

    assert not keypair.exists


def test_keypair_add_and_remove_tag(openstack_provider, keypairs):
    """ This will test whether it will add and remove tag for newly created Keypair or not
    and then deletes it.

    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Add tag to Keypair.
        * Remove tag from Keypair
        * Also delete it.
    """
    try:
        keypair = keypairs.create(name=fauxfactory.gen_alphanumeric(), provider=openstack_provider)
    except TimedOutError:
        if BZ(1444520, forced_streams=['5.6', '5.7', 'upstream']).blocks:
            pytest.skip('Timed out creating keypair, BZ1444520')
        else:
            pytest.fail('Timed out creating keypair')
    assert keypair.exists

    keypair.add_tag('Department', 'Accounting')
    tagged_value = keypair.get_tags()
    assert (
        tag.category.display_name == 'Department' and tag.display_name == 'Accounting'
        for tag in keypair.get_tags()), (
        'Assigned tag was not found on the details page')

    keypair.remove_tag('Department', 'Accounting')
    tagged_value1 = keypair.get_tags()
    assert tagged_value1 != tagged_value, "Remove tag failed."
    # Above small conversion in assert statement convert 'tagged_value' in tuple("a","b") and then
    # compare with tag which is tuple. As get_tags will return assigned tag in list format["a: b"].

    keypair.delete(wait=True)

    assert not keypair.exists
