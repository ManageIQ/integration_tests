import cfme.configure.access_control as ac
import fauxfactory
import pytest
from cfme import Credential, login
from cfme.common.vm import VM
from cfme.rest import a_provider as _a_provider
from cfme.rest import vm as _vm
from utils.providers import setup_a_provider
from utils import version

pytestmark = [pytest.mark.meta(blockers=[1276135])]


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


@pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
class TestVmOwnershipRESTAPI(object):
    @pytest.fixture(scope="module")
    def a_provider(self):
        return _a_provider()

    @pytest.fixture(scope="module")
    def vm(self, request, a_provider, rest_api):
        return _vm(request, a_provider, rest_api)

    def test_vm_set_ownership(self, rest_api, vm):
        if "set_ownership" not in rest_api.collections.services.action.all:
            pytest.skip("Set owner action for service is not implemented in this version")
        rest_vm = rest_api.collections.vms.get(name=vm)
        user = rest_api.collections.users.get(userid='admin')
        data = {
            "owner": {"href": user.href}
        }
        rest_vm.action.set_ownership(**data)
        rest_vm.reload()
        assert hasattr(rest_vm, "evm_owner_id")
        assert rest_vm.evm_owner_id == user.id

    def test_vms_set_ownership(self, rest_api, vm):
        if "set_ownership" not in rest_api.collections.services.action.all:
            pytest.skip("Set owner action for service is not implemented in this version")
        rest_vm = rest_api.collections.vms.get(name=vm)
        group = rest_api.collections.groups.get(description='EvmGroup-super_administrator')
        data = {
            "group": {"href": group.href}
        }
        rest_api.collections.vms.action.set_ownership(rest_vm, **data)
        rest_vm.reload()
        assert hasattr(rest_vm, "miq_group_id")
        assert rest_vm.miq_group_id == group.id

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_set_vm_owner(self, request, rest_api, vm, from_detail):
        """Test whether set_owner action from the REST API works.
        Prerequisities:
            * A VM
        Steps:
            * Find a VM id using REST
            * Call either:
                * POST /api/vms/<id> (method ``set_owner``) <- {"owner": "owner username"}
                * POST /api/vms (method ``set_owner``) <- {"owner": "owner username",
                    "resources": [{"href": ...}]}
            * Query the VM again
            * Assert it has the attribute ``evm_owner`` as we set it.
        Metadata:
            test_flag: rest
        """
        if "set_owner" not in rest_api.collections.vms.action.all:
            pytest.skip("Set owner action is not implemented in this version")
        rest_vm = rest_api.collections.vms.get(name=vm)
        if from_detail:
            assert rest_vm.action.set_owner(owner="admin")["success"], "Could not set owner"
        else:
            assert (
                len(rest_api.collections.vms.action.set_owner(rest_vm, owner="admin")) > 0,
                "Could not set owner")
        rest_vm.reload()
        assert hasattr(rest_vm, "evm_owner")
        assert rest_vm.evm_owner.userid == "admin"

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
