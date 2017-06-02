import pytest
from cfme import test_requirements
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import vm as _vm


pytestmark = [
    test_requirements.ownership,
]


class TestVmOwnershipRESTAPI(object):
    @pytest.fixture(scope="module")
    def a_provider(self, request):
        return _a_provider(request)

    @pytest.fixture(scope="module")
    def vm(self, request, a_provider, appliance):
        return _vm(request, a_provider, appliance.rest_api)

    @pytest.mark.tier(3)
    def test_vm_set_ownership(self, appliance, vm):
        """Tests set_ownership action from detail.

        Metadata:
            test_flag: rest
        """
        if "set_ownership" not in appliance.rest_api.collections.services.action.all:
            pytest.skip("Set owner action for service is not implemented in this version")
        rest_vm = appliance.rest_api.collections.vms.get(name=vm)
        user = appliance.rest_api.collections.users.get(userid='admin')
        data = {
            "owner": {"href": user.href}
        }
        rest_vm.action.set_ownership(**data)
        assert appliance.rest_api.response.status_code == 200
        rest_vm.reload()
        assert hasattr(rest_vm, "evm_owner_id")
        assert rest_vm.evm_owner_id == user.id

    @pytest.mark.tier(3)
    def test_vms_set_ownership(self, appliance, vm):
        """Tests set_ownership action from collection.

        Metadata:
            test_flag: rest
        """
        rest_vm = appliance.rest_api.collections.vms.get(name=vm)
        group = appliance.rest_api.collections.groups.get(
            description='EvmGroup-super_administrator')
        data = {
            "group": {"href": group.href}
        }
        appliance.rest_api.collections.vms.action.set_ownership(rest_vm, **data)
        assert appliance.rest_api.response.status_code == 200
        rest_vm.reload()
        assert hasattr(rest_vm, "miq_group_id")
        assert rest_vm.miq_group_id == group.id

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_set_vm_owner(self, appliance, vm, from_detail):
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
        rest_vm = appliance.rest_api.collections.vms.get(name=vm)
        if from_detail:
            responses = [rest_vm.action.set_owner(owner="admin")]
        else:
            responses = appliance.rest_api.collections.vms.action.set_owner(rest_vm, owner="admin")
        assert appliance.rest_api.response.status_code == 200
        for response in responses:
            assert response["success"] is True, "Could not set owner"
        rest_vm.reload()
        assert hasattr(rest_vm, "evm_owner_id")
        assert rest_vm.evm_owner.userid == "admin"
