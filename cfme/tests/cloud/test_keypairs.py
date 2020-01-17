import fauxfactory
import pytest
from Crypto.PublicKey import RSA

from cfme import test_requirements
from cfme.cloud.keypairs import KeyPairAllView
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.cloud,
    pytest.mark.usefixtures('has_no_providers_modscope', 'setup_provider_modscope'),
    pytest.mark.provider([EC2Provider, OpenStackProvider], scope="module")
]


@pytest.fixture()
def keypair(appliance, provider):
    key = appliance.collections.cloud_keypairs.create(
        name=fauxfactory.gen_alphanumeric(),
        provider=provider
    )
    assert key.exists
    yield key


@pytest.mark.meta(automates=[BZ(1718833)])
def test_keypair_crud(appliance, provider):
    """ This will test whether it will create new Keypair and then deletes it.
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: high
        initialEstimate: 1/4h
        testSteps:
            1. Create keypair.
            2. Read keypair.
            3. Delete keypair.
    """
    keypair = appliance.collections.cloud_keypairs.create(
        name=fauxfactory.gen_alphanumeric(),
        provider=provider
    )
    assert keypair.exists

    keypair.delete(wait=True)
    assert not keypair.exists


def test_keypair_crud_with_key(provider, appliance):
    """ This will test whether it will create new Keypair and then deletes it.
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: high
        initialEstimate: 1/4h
        testSteps:
            1. Create keypair.
            2. Read keypair.
            3. Delete keypair.
    """
    key = RSA.generate(1024)
    public_key = key.publickey().exportKey('OpenSSH').decode('utf-8')
    keypair = appliance.collections.cloud_keypairs.create(
        fauxfactory.gen_alphanumeric(),
        provider,
        public_key
    )
    assert keypair.exists

    keypair.delete(wait=True)
    assert not keypair.exists


def test_keypair_create_cancel(provider, appliance):
    """ This will test cancelling on adding a keypair
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Cancel creating keypair.
    """
    keypair = appliance.collections.cloud_keypairs.create(
        name="",
        provider=provider,
        cancel=True
    )
    assert not keypair.exists


def test_keypair_create_name_validation(provider, appliance):
    """ This will test validating that key pair without name cannot be created.
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Try to add key pair with empty name.
    """
    # test empty name
    keypair_collection = appliance.collections.cloud_keypairs
    view = navigate_to(keypair_collection, 'Add')
    view.fill({'provider': provider})
    assert not view.form.add.active

    # test invalid name - on ec2 any name can be specified so only testing openstack
    if provider.one_of(OpenStackProvider):
        view = navigate_to(keypair_collection, 'Add')
        keypair_name = '.?!_'
        view.form.fill({'name': keypair_name,
                   'provider': provider.name})
        view.form.add.click()
        view = view.browser.create_view(KeyPairAllView)
        view.flash.assert_message('Unable to create Key Pair "{}": Keypair data is invalid: '
                                  'Keypair name contains unsafe characters'.format(keypair_name))


def test_keypair_create_invalid_key_validation(provider, appliance):
    """ This will test validating that key pair with invalid public key cannot be created.
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: low
        initialEstimate: 1/4h
        testSteps:
            1. Try to add key pair with invalid public key.
    """
    invalid_key = fauxfactory.gen_alphanumeric()
    keypair_name = fauxfactory.gen_alphanumeric()
    keypair_collection = appliance.collections.cloud_keypairs
    view = navigate_to(keypair_collection, 'Add')
    view.form.fill({'name': keypair_name,
               'provider': provider.name,
               'public_key': invalid_key})
    view.form.add.click()
    view = view.browser.create_view(KeyPairAllView)
    if provider.one_of(EC2Provider):
        view.flash.assert_message('Unable to create Key Pair "{}": Key is not in valid OpenSSH '
                                  'public key format'.format(keypair_name))
    elif provider.one_of(OpenStackProvider):
        view.flash.assert_message('Unable to create Key Pair "{}": Keypair data is invalid: failed '
                                  'to generate fingerprint'.format(keypair_name))


@test_requirements.tag
@pytest.mark.provider([OpenStackProvider], scope="module", selector=ONE_PER_TYPE)
def test_keypair_add_and_remove_tag(keypair):
    """ This will test whether it will add and remove tag for newly created Keypair or not
    and then deletes it.
    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        initialEstimate: 1/4h
        testSteps:
            1. Create keypair.
            2. Read keypair.
            3. Add tag to Keypair.
            4. Remove tag from Keypair.
            5. Delete keypair.
    """
    added_tag = keypair.add_tag()
    assert added_tag in keypair.get_tags(), 'Assigned tag was not found on keypair'
    keypair.remove_tag(added_tag)
    assert added_tag not in keypair.get_tags(), "Remove tag failed."

    keypair.delete(wait=True)

    assert not keypair.exists


@pytest.mark.rfe
def test_download_private_key(keypair):
    """
    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/4h
    """
    keypair.download_private_key()


@pytest.mark.meta(automates=[1741635, 1747179])
@test_requirements.multi_tenancy
def test_keypair_visibility_in_tenants(appliance, child_tenant_admin_user):
    """
    Test to verify key pair visibility in tenants based on key pair ownership

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: high
        tags: cfme_tenancy
        initialEstimate: 1/4h
        testSteps:
            1. Copy the EvmRole_tenant_admin role to a new role (Since this role does not have the
               Auth Key Pairs feature enabled).
            2. Enable the Auth Key Pairs feature for the new role.
            3. Add either new or existing group to the newly created tenant admin role.
               (Steps 1-3 are done through fixtures)
            4. If the added group belongs to a child tenant, then the key pair is only visible to
               users in that group/child tenant and also users from groups that belong to parent
               tenants.
    """
    view = navigate_to(appliance.collections.cloud_keypairs, 'All')
    key_pair = view.entities.get_first_entity().data['name']
    key_pair_obj = appliance.collections.cloud_keypairs.instantiate(key_pair)
    key_pair_obj.set_ownership(group=child_tenant_admin_user.groups[0])
    view.flash.assert_success_message('Ownership saved for selected Key Pair')

    with child_tenant_admin_user:
        assert key_pair_obj.exists
