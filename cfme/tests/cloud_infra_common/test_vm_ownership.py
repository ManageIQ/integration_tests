from __future__ import unicode_literals
import cfme.configure.access_control as ac
import fauxfactory
import pytest
from cfme import Credential, login
from cfme.common.vm import VM
from utils import testgen


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.all_providers(metafunc, required_fields=['ownership_vm'])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


pytestmark = [
    pytest.mark.tier(3)
]


@pytest.yield_fixture(scope="module")
def role_only_user_owned():
    login.login_admin()
    role = ac.Role(name='role_only_user_owned_' + fauxfactory.gen_alphanumeric(),
                   vm_restriction='Only User Owned')
    role.create()
    yield role
    login.login_admin()
    role.delete()


@pytest.yield_fixture(scope="module")
def group_only_user_owned(role_only_user_owned):
    group = ac.Group(description='group_only_user_owned_' + fauxfactory.gen_alphanumeric(),
                     role=role_only_user_owned.name)
    group.create()
    yield group
    login.login_admin()
    group.delete()


@pytest.yield_fixture(scope="module")
def role_user_or_group_owned():
    login.login_admin()
    role = ac.Role(name='role_user_or_group_owned_' + fauxfactory.gen_alphanumeric(),
                   vm_restriction='Only User or Group Owned')
    role.create()
    yield role
    login.login_admin()
    role.delete()


@pytest.yield_fixture(scope="module")
def group_user_or_group_owned(role_user_or_group_owned):
    group = ac.Group(description='group_user_or_group_owned_' + fauxfactory.gen_alphanumeric(),
                     role=role_user_or_group_owned.name)
    group.create()
    yield group
    login.login_admin()
    group.delete()


def new_credential():
    return Credential(principal='uid' + fauxfactory.gen_alphanumeric(), secret='redhat')


@pytest.yield_fixture(scope="module")
def user1(group_only_user_owned):
    user1 = new_user(group_only_user_owned)
    yield user1
    login.login_admin()
    user1.delete()


@pytest.yield_fixture(scope="module")
def user2(group_only_user_owned):
    user2 = new_user(group_only_user_owned)
    yield user2
    login.login_admin()
    user2.delete()


@pytest.yield_fixture(scope="module")
def user3(group_user_or_group_owned):
    user3 = new_user(group_user_or_group_owned)
    yield user3
    login.login_admin()
    user3.delete()


def new_user(group_only_user_owned):
    user = ac.User(name='user_' + fauxfactory.gen_alphanumeric(),
                   credential=new_credential(),
                   email='abc@redhat.com',
                   group=group_only_user_owned,
                   cost_center='Workload',
                   value_assign='Database')
    user.create()
    return user


def test_form_button_validation(request, user1, setup_provider, provider):
    ownership_vm = provider.data['ownership_vm']
    user_ownership_vm = VM.factory(ownership_vm, provider)
    # Reset button test
    user_ownership_vm.set_ownership(user=user1.name, click_reset=True)
    # Cancel button test
    user_ownership_vm.set_ownership(user=user1.name, click_cancel=True)
    # Save button test
    user_ownership_vm.set_ownership(user=user1.name)
    # Unset the ownership
    user_ownership_vm.unset_ownership()


def test_user_ownership_crud(request, user1, setup_provider, provider):
    ownership_vm = provider.data['ownership_vm']
    user_ownership_vm = VM.factory(ownership_vm, provider)
    # Set the ownership and checking it
    user_ownership_vm.set_ownership(user=user1.name)
    with user1:
        assert user_ownership_vm.exists, "vm not found"
    user_ownership_vm.unset_ownership()
    with user1:
        assert not user_ownership_vm.exists, "vm exists"


def test_group_ownership_on_user_only_role(request, user2, setup_provider, provider):
    ownership_vm = provider.data['ownership_vm']
    group_ownership_vm = VM.factory(ownership_vm, provider)
    group_ownership_vm.set_ownership(group=user2.group.description)
    with user2:
        assert group_ownership_vm.exists, "vm not found"
    group_ownership_vm.unset_ownership()
    with user2:
        assert not group_ownership_vm.exists, "vm exists"


def test_group_ownership_on_user_or_group_role(
        request, user3, setup_provider, provider):
    ownership_vm = provider.data['ownership_vm']
    group_ownership_vm = VM.factory(ownership_vm, provider)
    group_ownership_vm.set_ownership(group=user3.group.description)
    with user3:
        assert group_ownership_vm.exists, "vm not found"
    group_ownership_vm.unset_ownership()
    with user3:
        assert not group_ownership_vm.exists, "vm exists"


# @pytest.mark.meta(blockers=[1202947])
# def test_ownership_transfer(request, user1, user3, setup_infra_provider):
#    user_ownership_vm = VM.factory('cu-9-5', setup_infra_provider)
#    user_ownership_vm.set_ownership(user=user1.name)
#    with user1:
#        # Checking before and after the ownership transfer
#        assert user_ownership_vm.exists, "vm not found"
#        user_ownership_vm.set_ownership(user=user3.name)
#        assert not user_ownership_vm.exists, "vm exists"
#    with user3:
#        assert user_ownership_vm.exists, "vm not found"
#    user_ownership_vm.unset_ownership()
#    with user3:
#        assert set_ownership_to_user.exists, "vm exists"
