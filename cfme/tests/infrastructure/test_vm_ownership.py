import cfme.configure.access_control as ac
import fauxfactory
import pytest
from cfme import Credential, login
from cfme.common.vm import VM
from utils.providers import setup_a_provider


@pytest.fixture(scope="module")
def setup_infra_provider():
    return setup_a_provider(prov_class="infra", validate=True, check_existing=True,
        required_keys=['ownership_vm'])


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
    login.login_admin()
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
    login.login_admin()
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
    login.login_admin()
    user1 = new_user(group_only_user_owned)
    yield user1
    login.login_admin()
    user1.delete()


@pytest.yield_fixture(scope="module")
def user2(group_only_user_owned):
    login.login_admin()
    user2 = new_user(group_only_user_owned)
    yield user2
    login.login_admin()
    user2.delete()


@pytest.yield_fixture(scope="module")
def user3(group_user_or_group_owned):
    login.login_admin()
    user3 = new_user(group_user_or_group_owned)
    yield user3
    login.login_admin()
    user3.delete()


def new_user(group_only_user_owned):
    login.login_admin()
    user = ac.User(name='user_' + fauxfactory.gen_alphanumeric(),
                credential=new_credential(),
                email='abc@redhat.com',
                group=group_only_user_owned,
                cost_center='Workload',
                value_assign='Database')
    user.create()
    return user


def test_form_button_validation(request, user1, setup_infra_provider):
    set_vm_to_user = VM.factory('cu-9-5', setup_infra_provider)
    # Reset button test
    set_vm_to_user.set_ownership(user=user1.name, click_reset=True)
    # Cancel button test
    set_vm_to_user.set_ownership(user=user1.name, click_cancel=True)
    # Save button test
    set_vm_to_user.set_ownership(user=user1.name)
    # Unset the ownership
    set_vm_to_user.unset_ownership()


def test_user_ownership_crud(request, user1, setup_infra_provider):
    set_vm_to_user = VM.factory('cu-9-5', setup_infra_provider)
    # Set the ownership and checking it
    set_vm_to_user.set_ownership(user=user1.name)
    with user1:
        assert(set_vm_to_user.exists, "vm not found")
    set_vm_to_user.unset_ownership()
    with user1:
        assert(not set_vm_to_user.exists, "vm exists")


def test_group_ownership_on_user_only_role(request, user2, setup_infra_provider):
    set_vm_to_group = VM.factory('cu-9-5', setup_infra_provider)
    set_vm_to_group.set_ownership(group=user2.group.description)
    with user2:
        assert(set_vm_to_group.exists, "vm not found")
    set_vm_to_group.unset_ownership()
    with user2:
        assert(not set_vm_to_group.exists, "vm exists")


def test_group_ownership_on_user_or_group_role(request, user3, setup_infra_provider):
    set_vm_to_group = VM.factory('cu-9-5', setup_infra_provider)
    set_vm_to_group.set_ownership(group=user3.group.description)
    with user3:
        assert(set_vm_to_group.exists, "vm not found")
    set_vm_to_group.unset_ownership()
    with user3:
        assert(not set_vm_to_group.exists, "vm exists")


# @pytest.mark.meta(blockers=[1202947])
# def test_ownership_transfer(request, user1, user3, setup_infra_provider):
#    set_vm_to_user = VM.factory('cu-9-5', setup_infra_provider)
#    set_vm_to_user.set_ownership(user=user1.name)
#    with user1:
#        # Checking before and after the ownership transfer
#        assert(set_vm_to_user.exists, "vm not found")
#        set_vm_to_user.set_ownership(user=user3.name)
#        assert(not set_vm_to_user.exists, "vm exists")
#    with user3:
#        assert(set_vm_to_user.exists, "vm not found")
#    set_vm_to_user.unset_ownership()
#    with user3:
#        assert(set_vm_to_user.exists, "vm exists")
