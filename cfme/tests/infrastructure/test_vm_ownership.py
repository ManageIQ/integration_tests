import pytest
from cfme.rest import a_provider as _a_provider
from cfme.rest import vm as _vm
from utils import version

pytestmark = [pytest.mark.meta(blockers=[1276135])]


@pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
class TestVmOwnershipRESTAPI(object):
    @pytest.fixture(scope="module")
    def a_provider(self):
        return _a_provider()

    @pytest.fixture(scope="module")
    def vm(self, request, a_provider, rest_api):
        return _vm(request, a_provider, rest_api)

    @pytest.mark.tier(3)
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

    @pytest.mark.tier(3)
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

    @pytest.mark.tier(3)
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
            assert len(rest_api.collections.vms.action.set_owner(rest_vm, owner="admin")) > 0,\
                "Could not set owner"
        rest_vm.reload()
        assert hasattr(rest_vm, "evm_owner")
        assert rest_vm.evm_owner.userid == "admin"
