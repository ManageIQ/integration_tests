import fauxfactory
import pytest

from cfme import test_requirements
from cfme.control.explorer.policies import VMControlPolicy
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.services.myservice import MyService
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import cfme_data
from cfme.utils.conf import credentials
from cfme.utils.update import update
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.long_running,
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE, scope="module"),
    test_requirements.ansible,
]


@pytest.fixture(scope="module")
def wait_for_ansible(appliance):
    appliance.server.settings.enable_server_roles("embedded_ansible")
    appliance.wait_for_embedded_ansible()
    yield
    appliance.server.settings.disable_server_roles("embedded_ansible")


@pytest.fixture(scope="module")
def ansible_repository(appliance, wait_for_ansible):
    repositories = appliance.collections.ansible_repositories
    try:
        repository = repositories.create(
            name=fauxfactory.gen_alpha(),
            url=cfme_data.ansible_links.playbook_repositories.embedded_ansible,
            description=fauxfactory.gen_alpha())
    except KeyError:
        pytest.skip("Skipping since no such key found in yaml")
    view = navigate_to(repository, "Details")
    wait_for(
        lambda: view.entities.summary("Properties").get_text_of("Status") == "successful",
        timeout=60,
        fail_func=view.toolbar.refresh.click
    )
    yield repository

    repository.delete_if_exists()


@pytest.fixture(scope="module")
def ansible_catalog_item(appliance, ansible_repository):
    cat_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.ANSIBLE_PLAYBOOK,
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
    yield cat_item

    cat_item.delete_if_exists()


@pytest.fixture(scope="module")
def ansible_action(appliance, ansible_catalog_item):
    action_collection = appliance.collections.actions
    action = action_collection.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Run Ansible Playbook",
        action_values={
            "run_ansible_playbook": {
                "playbook_catalog_item": ansible_catalog_item.name
            }
        }
    )
    yield action

    action.delete_if_exists()


@pytest.fixture(scope="module")
def policy_for_testing(appliance, full_template_vm_modscope, provider, ansible_action):
    vm = full_template_vm_modscope
    policy = appliance.collections.policies.create(
        VMControlPolicy,
        fauxfactory.gen_alpha(),
        scope="fill_field(VM and Instance : Name, INCLUDES, {})".format(vm.name)
    )
    policy.assign_actions_to_event("Tag Complete", [ansible_action.description])
    policy_profile = appliance.collections.policy_profiles.create(
        fauxfactory.gen_alpha(), policies=[policy])
    provider.assign_policy_profiles(policy_profile.description)
    yield

    if policy.exists:
        policy.assign_events()
        provider.unassign_policy_profiles(policy_profile.description)
        policy_profile.delete()
        policy.delete()


@pytest.fixture(scope="module")
def ansible_credential(wait_for_ansible, appliance, full_template_modscope):
    credential = appliance.collections.ansible_credentials.create(
        fauxfactory.gen_alpha(),
        "Machine",
        username=credentials[full_template_modscope.creds]["username"],
        password=credentials[full_template_modscope.creds]["password"]
    )
    yield credential

    credential.delete_if_exists()


@pytest.fixture
def service_request(appliance, ansible_catalog_item):
    request_desc = "Provisioning Service [{0}] from [{0}]".format(ansible_catalog_item.name)
    _service_request = appliance.collections.requests.instantiate(request_desc)
    yield _service_request

    _service_request.delete_if_exists()


@pytest.fixture
def service(appliance, ansible_catalog_item):
    service_ = MyService(appliance, ansible_catalog_item.name)
    yield service_

    if service_.exists:
        service_.delete()


@pytest.mark.tier(3)
def test_action_run_ansible_playbook_localhost(request, ansible_catalog_item, ansible_action,
        policy_for_testing, full_template_vm_modscope, ansible_credential, service_request,
        service):
    """Tests a policy with ansible playbook action against localhost.

    Polarion:
        assignee: sbulage
        initialEstimate: 1/6h
        casecomponent: Ansible
    """
    with update(ansible_action):
        ansible_action.run_ansible_playbook = {"inventory": {"localhost": True}}
    added_tag = full_template_vm_modscope.add_tag()
    request.addfinalizer(lambda: full_template_vm_modscope.remove_tag(added_tag))
    wait_for(service_request.exists, num_sec=600)
    service_request.wait_for_request()
    view = navigate_to(service, "Details")
    assert view.provisioning.details.get_text_of("Hosts") == "localhost"
    assert view.provisioning.results.get_text_of("Status") == "successful"


@pytest.mark.tier(3)
def test_action_run_ansible_playbook_manual_address(request, ansible_catalog_item, ansible_action,
        policy_for_testing, full_template_vm_modscope, ansible_credential, service_request,
        service):
    """Tests a policy with ansible playbook action against manual address.

    Polarion:
        assignee: sbulage
        initialEstimate: 1/6h
        casecomponent: Ansible
    """
    vm = full_template_vm_modscope
    with update(ansible_catalog_item):
        ansible_catalog_item.provisioning = {"machine_credential": ansible_credential.name}
    with update(ansible_action):
        ansible_action.run_ansible_playbook = {
            "inventory": {
                "specific_hosts": True,
                "hosts": vm.ip_address
            }
        }
    added_tag = vm.add_tag()
    request.addfinalizer(lambda: vm.remove_tag(added_tag))
    wait_for(service_request.exists, num_sec=600)
    service_request.wait_for_request()
    view = navigate_to(service, "Details")
    assert view.provisioning.details.get_text_of("Hosts") == vm.ip_address
    assert view.provisioning.results.get_text_of("Status") == "successful"


@pytest.mark.tier(3)
def test_action_run_ansible_playbook_target_machine(request, ansible_catalog_item, ansible_action,
        policy_for_testing, full_template_vm_modscope, ansible_credential, service_request,
        service):
    """Tests a policy with ansible playbook action against target machine.

    Polarion:
        assignee: sbulage
        initialEstimate: 1/6h
        casecomponent: Ansible
    """
    vm = full_template_vm_modscope
    with update(ansible_action):
        ansible_action.run_ansible_playbook = {"inventory": {"target_machine": True}}
    added_tag = vm.add_tag()
    request.addfinalizer(lambda: vm.remove_tag(added_tag))
    wait_for(service_request.exists, num_sec=600)
    service_request.wait_for_request()
    view = navigate_to(service, "Details")
    assert view.provisioning.details.get_text_of("Hosts") == vm.ip_address
    assert view.provisioning.results.get_text_of("Status") == "successful"


@pytest.mark.tier(3)
def test_action_run_ansible_playbook_unavailable_address(request, ansible_catalog_item,
        full_template_vm_modscope, ansible_action, policy_for_testing, ansible_credential,
        service_request, service):
    """Tests a policy with ansible playbook action against unavailable address.

    Polarion:
        assignee: sbulage
        initialEstimate: 1/6h
        casecomponent: Ansible
    """
    vm = full_template_vm_modscope
    with update(ansible_catalog_item):
        ansible_catalog_item.provisioning = {"machine_credential": ansible_credential.name}
    with update(ansible_action):
        ansible_action.run_ansible_playbook = {
            "inventory": {
                "specific_hosts": True,
                "hosts": "unavailable_address"
            }
        }
    added_tag = vm.add_tag()
    request.addfinalizer(lambda: vm.remove_tag(added_tag))
    wait_for(service_request.exists, num_sec=600)
    service_request.wait_for_request()
    view = navigate_to(service, "Details")
    assert view.provisioning.details.get_text_of("Hosts") == "unavailable_address"
    assert view.provisioning.results.get_text_of("Status") == "failed"


@pytest.mark.tier(3)
def test_control_action_run_ansible_playbook_in_requests(request,
        full_template_vm_modscope, policy_for_testing, service_request):
    """Checks if execution of the Action result in a Task/Request being created.

    Polarion:
        assignee: sbulage
        initialEstimate: 1/6h
        casecomponent: Ansible
    """
    vm = full_template_vm_modscope
    added_tag = vm.add_tag()
    request.addfinalizer(lambda: vm.remove_tag(added_tag))
    assert service_request.exists
