import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.cloud.provider import CloudProvider
from cfme.exceptions import VmOrInstanceNotFound
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger

pytestmark = [
    test_requirements.ownership,
    pytest.mark.meta(blockers=[BZ(1380781, forced_streams=["5.7"])]),
    pytest.mark.tier(3),
    pytest.mark.provider([CloudProvider, InfraProvider], scope='module')
]


@pytest.fixture(scope="module")
def vm_crud(provider):
    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.instantiate(random_vm_name(context='ownrs'), provider)
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    yield vm

    try:
        vm.cleanup_on_provider()
    except Exception:
        logger.exception('Exception deleting test vm "%s" on %s', vm.name, provider.name)


@pytest.fixture(scope="module")
def role_only_user_owned(appliance):
    appliance.server.login_admin()
    role = appliance.collections.roles.create(
        name='role_only_user_owned_' + fauxfactory.gen_alphanumeric(),
        vm_restriction='Only User Owned'
    )
    yield role
    appliance.server.login_admin()
    role.delete()


@pytest.fixture(scope="module")
def group_only_user_owned(appliance, role_only_user_owned):
    group_collection = appliance.collections.groups
    group = group_collection.create(
        description='group_only_user_owned_{}'.format(fauxfactory.gen_alphanumeric()),
        role=role_only_user_owned.name)
    yield group
    appliance.server.login_admin()
    group.delete()


@pytest.fixture(scope="module")
def role_user_or_group_owned(appliance):
    appliance.server.login_admin()
    role = appliance.collections.roles.create(
        name='role_user_or_group_owned_' + fauxfactory.gen_alphanumeric(),
        vm_restriction='Only User or Group Owned'
    )
    yield role
    appliance.server.login_admin()
    role.delete()


@pytest.fixture(scope="module")
def group_user_or_group_owned(appliance, role_user_or_group_owned):
    group_collection = appliance.collections.groups
    group = group_collection.create(
        description='group_user_or_group_owned_{}'.format(fauxfactory.gen_alphanumeric()),
        role=role_user_or_group_owned.name)
    yield group
    appliance.server.login_admin()
    group.delete()


def new_credential():
    # BZ1487199 - CFME allows usernames with uppercase chars which blocks logins
    if BZ.bugzilla.get_bug(1487199).is_opened:
        return Credential(principal='uid' + fauxfactory.gen_alphanumeric().lower(), secret='redhat')
    else:
        return Credential(principal='uid' + fauxfactory.gen_alphanumeric(), secret='redhat')


@pytest.fixture(scope="module")
def user1(appliance, group_only_user_owned):
    user1 = new_user(appliance, group_only_user_owned)
    yield user1
    appliance.server.login_admin()
    user1.delete()


@pytest.fixture(scope="module")
def user2(appliance, group_only_user_owned):
    user2 = new_user(appliance, group_only_user_owned)
    yield user2
    appliance.server.login_admin()
    user2.delete()


@pytest.fixture(scope="module")
def user3(appliance, group_user_or_group_owned):
    user3 = new_user(appliance, group_user_or_group_owned)
    yield user3
    appliance.server.login_admin()
    user3.delete()


def new_user(appliance, group_only_user_owned):
    user = appliance.collections.users.create(
        name='user_' + fauxfactory.gen_alphanumeric(),
        credential=new_credential(),
        email='abc@redhat.com',
        groups=[group_only_user_owned],
        cost_center='Workload',
        value_assign='Database'
    )
    return user


def check_vm_exists(vm_ownership):
    """ Checks if VM exists through All Instances tab.

    Args:
        vm_ownership: VM object for ownership test

    Returns:
        :py:class:`bool`
    """
    try:
        vm_ownership.find_quadicon(from_any_provider=True)
        return True
    except VmOrInstanceNotFound:
        return False


@pytest.mark.rhv3
def test_form_button_validation(request, user1, setup_provider, provider, vm_crud):
    """Tests group ownership

    Metadata:
        test_flag: rbac
    """
    # Reset button test
    vm_crud.set_ownership(user=user1, click_reset=True)
    # Cancel button test
    vm_crud.set_ownership(user=user1, click_cancel=True)
    # Save button test
    vm_crud.set_ownership(user=user1)
    # Unset the ownership
    vm_crud.unset_ownership()


@pytest.mark.rhv2
def test_user_ownership_crud(request, user1, setup_provider, provider, vm_crud):
    """Tests user ownership

    Metadata:
        test_flag: rbac
    """
    # Set the ownership and checking it
    vm_crud.set_ownership(user=user1)
    with user1:
        assert vm_crud.exists, "vm not found"
    vm_crud.unset_ownership()
    with user1:
        assert not check_vm_exists(vm_crud), "vm exists! but shouldn't exist"


@pytest.mark.rhv3
def test_group_ownership_on_user_only_role(request, user2, setup_provider, provider, vm_crud):
    """Tests group ownership

    Metadata:
        test_flag: rbac
    """

    # user is only a member of a single group so it will always be the current group
    vm_crud.set_ownership(group=user2.group)
    with user2:
        assert not check_vm_exists(vm_crud), "vm exists! but shouldn't exist"
    vm_crud.set_ownership(user=user2)
    with user2:
        assert vm_crud.exists, "vm exists"


@pytest.mark.rhv3
def test_group_ownership_on_user_or_group_role(
        request, user3, setup_provider, provider, vm_crud):
    """Tests group ownership

    Metadata:
        test_flag: rbac
    """
    # user is only a member of a single group so it will always be the current group
    vm_crud.set_ownership(group=user3.group)
    with user3:
        assert vm_crud.exists, "vm not found"
    vm_crud.unset_ownership()
    with user3:
        assert not check_vm_exists(vm_crud), "vm exists! but shouldn't exist"


@pytest.mark.provider([VMwareProvider], override=True, scope="module")
def test_template_set_ownership(request, provider, setup_provider, vm_crud):
    """ Sets ownership to an infra template.

    First publishes a template from a VM, then tries to unset an ownership of that template,
    then sets it back and in the end removes the template.
    VM is removed via fixture.
    Tests BZ 1446801 in RHCF3-14353
    """
    template = vm_crud.publish_to_template(template_name=random_vm_name(context='ownrs'))
    template.set_ownership('<No Owner>')
    template.set_ownership('Administrator')
    template.delete()


# @pytest.mark.meta(blockers=[1202947])
# def test_ownership_transfer(appliance, request, user1, user3, setup_infra_provider):
#    user_ownership_vm = appliance.collections.infra_vms.instantiate('cu-9-5', setup_infra_provider)
#    user_ownership_vm.set_ownership(user=user1.name)
#    with user1:
#        # Checking before and after the ownership transfer
#        assert user_ownership_vm.exists, "vm not found"
#        user_ownership_vm.set_ownership(user=user3)
#        assert not user_ownership_vm.exists, "vm exists"
#    with user3:
#        assert user_ownership_vm.exists, "vm not found"
#    user_ownership_vm.unset_ownership()
#    with user3:
#        assert set_ownership_to_user.exists, "vm exists"
