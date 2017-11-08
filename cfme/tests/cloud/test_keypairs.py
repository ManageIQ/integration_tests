import fauxfactory
import pytest
from Crypto.PublicKey import RSA

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.blockers import BZ
from cfme.utils.wait import TimedOutError

pytestmark = [pytest.mark.usefixtures('setup_provider'),
              pytest.mark.provider([OpenStackProvider], scope="module")]


@pytest.mark.tier(3)
def test_keypair_crud(appliance, openstack_provider):
    """ This will test whether it will create new Keypair and then deletes it.
    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Also delete it.
    """
    kp_collection = appliance.collections.keypairs
    try:
        keypair = kp_collection.create(
            name=fauxfactory.gen_alphanumeric(), provider=openstack_provider
        )
    except TimedOutError:
        if BZ(1444520, forced_streams=['5.6', '5.7', 'upstream']).blocks:
            pytest.skip('Timed out creating keypair, BZ1444520')
        else:
            pytest.fail('Timed out creating keypair')
    assert keypair.exists

    keypair.delete(wait=True)
    assert not keypair.exists


@pytest.mark.tier(3)
def test_keypair_crud_with_key(appliance, openstack_provider):
    """ This will test whether it will create new Keypair and then deletes it.

    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Also delete it.
    """
    key = RSA.generate(1024)
    public_key = key.publickey().exportKey('OpenSSH')
    kp_collection = appliance.collections.keypairs
    try:
        keypair = kp_collection.create(
            name=fauxfactory.gen_alphanumeric(), provider=openstack_provider, public_key=public_key
        )
    except TimedOutError:
        if BZ(1444520, forced_streams=['5.6', '5.7', 'upstream']).blocks:
            pytest.skip('Timed out creating keypair, BZ1444520')
        else:
            pytest.fail('Timed out creating keypair')
    assert keypair.exists

    keypair.delete(wait=True)
    assert not keypair.exists


@pytest.mark.tier(3)
def test_keypair_create_cancel(appliance, openstack_provider):
    """ This will test cancelling on adding a keypair

    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Also delete it.
    """
    kp_collection = appliance.collections.keypairs
    keypair = kp_collection.create(
        name=fauxfactory.gen_alphanumeric(), provider=openstack_provider, cancel=True
    )

    assert not keypair.exists


def test_keypair_add_and_remove_tag(appliance, openstack_provider):
    """ This will test whether it will add and remove tag for newly created Keypair or not
    and then deletes it.

    Steps:
        * Provide Keypair name.
        * Select Cloud Provider.
        * Add tag to Keypair.
        * Remove tag from Keypair
        * Also delete it.
    """

    kp_collection = appliance.collections.keypairs

    try:
        keypair = kp_collection.create(
            name=fauxfactory.gen_alphanumeric(), provider=openstack_provider
        )
    except TimedOutError:
        if BZ(1444520, forced_streams=['5.6', '5.7', 'upstream']).blocks:
            pytest.skip('Timed out creating keypair, BZ1444520')
        else:
            pytest.fail('Timed out creating keypair')

    assert keypair.exists

    # add tag
    keypair.add_tag('Department', 'Accounting')
    tagged_value = keypair.get_tags()
    assert tagged_value[0].display_name == 'Accounting'
    assert tagged_value[0].category.display_name == 'Department'

    # remove tag
    keypair.remove_tag('Department', 'Accounting')
    tagged_value = keypair.get_tags()
    assert not tagged_value

    keypair.delete(wait=True)
    assert not keypair.exists
