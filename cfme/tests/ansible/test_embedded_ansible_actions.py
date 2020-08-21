import fauxfactory
import pytest

from cfme import test_requirements
from cfme.control.explorer.policies import VMControlPolicy
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials
from cfme.utils.update import update
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.long_running,
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE, scope="module"),
    test_requirements.ansible,
]


@pytest.fixture(scope="function")
def ansible_action(appliance, ansible_catalog_item):
    action_collection = appliance.collections.actions
    action = action_collection.create(
        fauxfactory.gen_alphanumeric(15, start="action_"),
        action_type="Run Ansible Playbook",
        action_values={
            "run_ansible_playbook": {"playbook_catalog_item": ansible_catalog_item.name}
        },
    )
    yield action

    action.delete_if_exists()


@pytest.fixture(scope="function")
def policy_for_testing(appliance, create_vm, provider, ansible_action):
    policy = appliance.collections.policies.create(
        VMControlPolicy,
        fauxfactory.gen_alpha(15, start="policy_"),
        scope=f"fill_field(VM and Instance : Name, INCLUDES, {create_vm.name})",
    )
    policy.assign_actions_to_event("Tag Complete", [ansible_action.description])
    policy_profile = appliance.collections.policy_profiles.create(
        fauxfactory.gen_alpha(15, start="profile_"), policies=[policy]
    )
    provider.assign_policy_profiles(policy_profile.description)
    yield

    if policy.exists:
        policy.unassign_events("Tag Complete")
        provider.unassign_policy_profiles(policy_profile.description)
        policy_profile.delete()
        policy.delete()


@pytest.fixture(scope="module")
def ansible_credential(wait_for_ansible, appliance, full_template_modscope):
    credential = appliance.collections.ansible_credentials.create(
        fauxfactory.gen_alpha(start="cred_"),
        "Machine",
        username=credentials[full_template_modscope.creds]["username"],
        password=credentials[full_template_modscope.creds]["password"],
    )
    yield credential

    credential.delete_if_exists()


@pytest.mark.tier(3)
@pytest.mark.parametrize("create_vm", ["full_template"], indirect=True)
def test_action_run_ansible_playbook_localhost(
    request,
    ansible_catalog_item,
    ansible_action,
    policy_for_testing,
    create_vm,
    ansible_credential,
    ansible_service_request,
    ansible_service,
    appliance,
):
    """Tests a policy with ansible playbook action against localhost.

    Polarion:
        assignee: gtalreja
        initialEstimate: 1/6h
        casecomponent: Ansible
    """
    with update(ansible_action):
        ansible_action.run_ansible_playbook = {"inventory": {"localhost": True}}
    create_vm.add_tag()
    wait_for(ansible_service_request.exists, num_sec=600)
    ansible_service_request.wait_for_request()
    view = navigate_to(ansible_service, "Details")
    assert view.provisioning.details.get_text_of("Hosts") == "localhost"
    assert view.provisioning.results.get_text_of("Status") == "Finished"


@pytest.mark.meta(blockers=[BZ(1822533, forced_streams=["5.11", "5.10"])])
@pytest.mark.tier(3)
@pytest.mark.parametrize("create_vm", ["full_template"], indirect=True)
def test_action_run_ansible_playbook_manual_address(
    request,
    ansible_catalog_item,
    ansible_action,
    policy_for_testing,
    create_vm,
    ansible_credential,
    ansible_service_request,
    ansible_service,
    appliance,
):
    """Tests a policy with ansible playbook action against manual address.

    Polarion:
        assignee: gtalreja
        initialEstimate: 1/6h
        casecomponent: Ansible
    """
    with update(ansible_catalog_item):
        ansible_catalog_item.provisioning = {"machine_credential": ansible_credential.name}
    with update(ansible_action):
        ansible_action.run_ansible_playbook = {
            "inventory": {"specific_hosts": True, "hosts": create_vm.ip_address}
        }
    create_vm.add_tag()
    wait_for(ansible_service_request.exists, num_sec=600)
    ansible_service_request.wait_for_request()
    view = navigate_to(ansible_service, "Details")
    assert view.provisioning.details.get_text_of("Hosts") == create_vm.ip_address
    assert view.provisioning.results.get_text_of("Status") == "Finished"


@pytest.mark.meta(blockers=[BZ(1822533, forced_streams=["5.11", "5.10"])])
@pytest.mark.tier(3)
@pytest.mark.parametrize("create_vm", ["full_template"], indirect=True)
def test_action_run_ansible_playbook_target_machine(
    request,
    ansible_catalog_item,
    ansible_action,
    policy_for_testing,
    create_vm,
    ansible_credential,
    ansible_service_request,
    ansible_service,
    appliance,
):
    """Tests a policy with ansible playbook action against target machine.

    Polarion:
        assignee: gtalreja
        initialEstimate: 1/6h
        casecomponent: Ansible
    """
    with update(ansible_action):
        ansible_action.run_ansible_playbook = {"inventory": {"target_machine": True}}
    create_vm.add_tag()
    wait_for(ansible_service_request.exists, num_sec=600)
    ansible_service_request.wait_for_request()
    view = navigate_to(ansible_service, "Details")
    assert view.provisioning.details.get_text_of("Hosts") == create_vm.ip_address
    assert view.provisioning.results.get_text_of("Status") == "Finished"


@pytest.mark.tier(3)
@pytest.mark.parametrize("create_vm", ["full_template"], indirect=True)
def test_action_run_ansible_playbook_unavailable_address(
    request,
    ansible_catalog_item,
    create_vm,
    ansible_action,
    policy_for_testing,
    ansible_credential,
    ansible_service_request,
    ansible_service,
    appliance,
):
    """Tests a policy with ansible playbook action against unavailable address.

    Polarion:
        assignee: gtalreja
        initialEstimate: 1/6h
        casecomponent: Ansible
    """
    with update(ansible_catalog_item):
        ansible_catalog_item.provisioning = {"machine_credential": ansible_credential.name}
    with update(ansible_action):
        ansible_action.run_ansible_playbook = {
            "inventory": {"specific_hosts": True, "hosts": "unavailable_address"}
        }
    create_vm.add_tag()
    wait_for(ansible_service_request.exists, num_sec=600)
    ansible_service_request.wait_for_request()
    view = navigate_to(ansible_service, "Details")
    assert view.provisioning.details.get_text_of("Hosts") == "unavailable_address"
    assert view.provisioning.results.get_text_of("Status") == "Finished"
