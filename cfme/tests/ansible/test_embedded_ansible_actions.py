import fauxfactory
import pytest

from cfme import test_requirements
from cfme.ansible.repositories import RepositoryCollection
from cfme.ansible.credentials import CredentialsCollection
from cfme.common.vm import VM
from cfme.control.explorer.actions import Action
from cfme.control.explorer.policies import VMControlPolicy
from cfme.control.explorer.policy_profiles import PolicyProfile
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.services.catalogs.ansible_catalog_item import AnsiblePlaybookCatalogItem
from cfme.services.myservice import MyService
from cfme.services.requests import Request
from fixtures.provider import setup_one_by_class_or_skip
from utils import ports
from utils.appliance.implementations.ui import navigate_to
from utils.conf import credentials
from utils.generators import random_vm_name
from utils.net import net_check
from utils.update import update
from utils.version import current_version
from utils.wait import wait_for


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(server_roles=["+embedded_ansible"]),
    pytest.mark.uncollectif(lambda: current_version() < "5.8"),
    pytest.mark.ignore_stream("upstream"),
    test_requirements.ansible
]


ANSIBLE_ACTION_VALUES = [
    (
        "localhost",
        {"inventory": {"localhost": True}}
    ),
    (
        "manual_address",
        {"inventory": {"specific_hosts": True, "hosts": None}}
    ),
    (
        "target_machine",
        {"inventory": {"target_machine": True}}
    ),
    (
        "unavailable_address",
        {"inventory": {"specific_hosts": True, "hosts": "unavailable_address"}}
    )
]


@pytest.fixture(scope="module")
def provider(request):
    return setup_one_by_class_or_skip(request, VMwareProvider)


@pytest.fixture(scope="module")
def wait_for_ansible(appliance):
    appliance.wait_for_embedded_ansible()


@pytest.yield_fixture(scope="module")
def ansible_repository(wait_for_ansible):
    repositories = RepositoryCollection()
    repository = repositories.create(
        fauxfactory.gen_alpha(),
        "https://github.com/quarckster/ansible_playbooks",
        description=fauxfactory.gen_alpha()
    )
    yield repository
    repository.delete()


@pytest.yield_fixture(scope="module")
def ansible_catalog_item(ansible_repository):
    cat_item = AnsiblePlaybookCatalogItem(
        fauxfactory.gen_alphanumeric(),
        fauxfactory.gen_alphanumeric(),
        display_in_catalog=True,
        provisioning={
            "repository": ansible_repository.name,
            "playbook": "dump_all_variables.yml",
            "machine_credential": "CFME Default Credential",
            "create_new": True,
            "provisioning_dialog_name": fauxfactory.gen_alphanumeric()
        }
    )
    cat_item.create()
    yield cat_item
    cat_item.delete()


@pytest.yield_fixture(scope="module")
def vmware_vm(full_template_modscope, provider):
    vm_obj = VM.factory(random_vm_name("ansible"), provider, template_name=full_template_modscope)
    vm_obj.create_on_provider(allow_skip="default")
    provider.mgmt.start_vm(vm_obj.name)
    provider.mgmt.wait_vm_running(vm_obj.name)
    # In order to have seamless SSH connection
    vm_ip, _ = wait_for(
        lambda: provider.mgmt.current_ip_address(vm_obj.name),
        num_sec=300, delay=5, fail_condition={None}, message="wait for testing VM IP address.")
    wait_for(
        net_check, [ports.SSH, vm_ip], {"force": True},
        num_sec=300, delay=5, message="testing VM's SSH available")
    if not vm_obj.exists:
        provider.refresh_provider_relationships()
        vm_obj.wait_to_appear()
    yield vm_obj
    if provider.mgmt.does_vm_exist(vm_obj.name):
        provider.mgmt.delete_vm(vm_obj.name)
    provider.refresh_provider_relationships()


@pytest.yield_fixture(scope="module")
def ansible_action(ansible_catalog_item):
    action = Action(
        fauxfactory.gen_alphanumeric(),
        action_type="Run Ansible Playbook",
        action_values={
            "run_ansible_playbook": {
                "playbook_catalog_item": ansible_catalog_item.name
            }
        }
    )
    action.create()
    yield action
    action.delete()


@pytest.yield_fixture(scope="module")
def policy_for_testing(vmware_vm, provider, ansible_action):
    policy = VMControlPolicy(
        fauxfactory.gen_alpha(),
        scope="fill_field(VM and Instance : Name, INCLUDES, {})".format(vmware_vm.name)
    )
    policy.create()
    policy.assign_actions_to_event("Tag Complete", [ansible_action.description])
    policy_profile = PolicyProfile(fauxfactory.gen_alpha(), policies=[policy])
    policy_profile.create()
    provider.assign_policy_profiles(policy_profile.description)
    yield
    policy.assign_events()
    provider.unassign_policy_profiles(policy_profile.description)
    policy_profile.delete()
    policy.delete()


@pytest.yield_fixture(scope="module")
def ansible_credential(full_template_modscope):
    credential = CredentialsCollection().create(
        fauxfactory.gen_alpha(),
        "Machine",
        username=credentials[full_template_modscope]["username"],
        password=credentials[full_template_modscope]["password"]
    )
    yield credential
    credential.delete()


@pytest.yield_fixture
def service_request(ansible_catalog_item):
    request_desc = "Provisioning Service [{0}] from [{0}]".format(ansible_catalog_item.name)
    service_request_ = Request(request_desc)
    yield service_request_
    service_request_.remove_request()


@pytest.yield_fixture
def service(ansible_catalog_item):
    service_ = MyService(ansible_catalog_item.name)
    yield service_
    service_.delete()


@pytest.mark.tier(3)
@pytest.mark.parametrize("host_type,inventory", ANSIBLE_ACTION_VALUES, ids=[
    value[0] for value in ANSIBLE_ACTION_VALUES])
def test_action_run_ansible_playbook(request, full_template, ansible_catalog_item, ansible_action,
        policy_for_testing, vmware_vm, ansible_credential, service_request, service, host_type,
        inventory):
    """Tests a policy with ansible playbook action against localhost, manual address,
       target machine and unavailable address.
    """
    if host_type == "manual_address":
        inventory["inventory"]["hosts"] = vmware_vm.ip_address
    if host_type in ["manual_address", "target_machine"]:
        with update(ansible_catalog_item):
            ansible_catalog_item.provisioning = {"machine_credential": ansible_credential.name}
    with update(ansible_action):
        ansible_action.run_ansible_playbook = inventory
    vmware_vm.add_tag(("Service Level", "Gold"), single_value=True)
    request.addfinalizer(lambda: vmware_vm.remove_tag(("Service Level", "Gold")))
    wait_for(service_request.exists, num_sec=600)
    service_request.wait_for_request()
    view = navigate_to(service, "Details")
    if host_type == "localhost":
        assert view.provisioning.details.get_text_of("Hosts") == "localhost"
        assert view.provisioning.results.get_text_of("Status") == "successful"
    elif host_type == "manual_address":
        assert view.provisioning.details.get_text_of("Hosts") == vmware_vm.ip_address
        assert view.provisioning.results.get_text_of("Status") == "successful"
    elif host_type == "target_machine":
        assert view.provisioning.details.get_text_of("Hosts") == vmware_vm.ip_address
        assert view.provisioning.results.get_text_of("Status") == "successful"
    elif host_type == "unavailable_address":
        assert view.provisioning.details.get_text_of("Hosts") == "unavailable_address"
        assert view.provisioning.results.get_text_of("Status") == "failed"


@pytest.mark.tier(3)
def test_control_action_run_ansible_playbook_in_requests(request, vmware_vm, policy_for_testing,
        service_request):
    """Checks if execution of the Action result in a Task/Request being created."""
    vmware_vm.add_tag(("Service Level", "Gold"), single_value=True)
    request.addfinalizer(lambda: vmware_vm.remove_tag(("Service Level", "Gold")))
    assert service_request.exists
