import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE, ONE_PER_TYPE
from cfme.rest.gen_data import vm as _vm
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.rest import assert_response


pytestmark = [
    test_requirements.ownership,
    pytest.mark.provider(classes=[InfraProvider], selector=ONE),
    pytest.mark.usefixtures('setup_provider')
]


class TestVmOwnershipRESTAPI(object):
    @pytest.fixture(scope="module")
    def vm(self, request, provider, appliance):
        return _vm(request, provider, appliance.rest_api)

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
        assert_response(appliance)
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
        assert_response(appliance)
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
        assert_response(appliance)
        for response in responses:
            assert response["success"] is True, "Could not set owner"
        rest_vm.reload()
        assert hasattr(rest_vm, "evm_owner_id")
        assert rest_vm.evm_owner.userid == "admin"


@pytest.fixture(scope='module')
def small_vm(provider, small_template_modscope):
    vm = provider.appliance.collections.infra_vms.instantiate(random_vm_name(context='rename'),
                                                              provider,
                                                              small_template_modscope.name)
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    vm.refresh_relationships()
    yield vm
    vm.cleanup_on_provider()


@pytest.mark.ignore_stream('5.9')
@pytest.mark.provider([VMwareProvider], override=True, scope="module", selector=ONE_PER_TYPE)
def test_rename_vm(appliance, setup_provider, small_vm):

    """Test for rename the VM.
       This feature is included in 5.10z.
    Steps:
    1. Add VMware provider
    2. Provision VM
    3. Navigate to details page of VM
    4. Click on Configuration > Rename this VM > Enter new name
    5. Click on submit
    6. Check whether VM is renamed or not
    """
    view = navigate_to(small_vm, 'Details')
    changed_vm_name = small_vm.rename_vm(new_vm_name="test-{}".
                                         format(fauxfactory.gen_alphanumeric()))
    view.flash.wait_displayed("20s")
    msg = 'Rename of Virtual Machine "{vm_name}" has been initiated'.format(vm_name=small_vm.name)
    view.flash.assert_success_message(msg)
    assert changed_vm_name.exists
