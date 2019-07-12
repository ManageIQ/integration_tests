# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data
from cfme.utils.log import logger
from cfme.utils.update import update
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.meta(blockers=[BZ(1677548, forced_streams=["5.11"])]),
    test_requirements.ansible,
]

private_key = """
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA6J0DNbInTt35zDDq8obCRUH1uJvqoNEP+yEEHm/C1ipIC7vW
7ROuQMcPpsTgIVWBmFCOAt3TuQASYqo0mQrRHRPFDD0msPMMLcWENJ+4HkPZaZZX
k38HNuxa9NqPi5x/v008g4bER9OrleA2v5QPJHhcfLAjdL104gGeAK0G7+xJoJDA
NishuOkGC/qVBCaQ6qrEBlVHq6v5eSgXSJz3Jdd6GBdHy2xfokYHIEAb+qt3mW0G
ijXPBXDtBVguQ2OIJgEzmMh7sAjnAqogrH8FGRJUB+y7dqhZfmJSmSImoFo9/Akk
Ei+QbgijymVDmCLL16u7I9q6tHOVuhf9e3I0aQIDAQABAoIBAAuzwnKUGNgl4Kg+
GcPDtchILjVwWphmjBhFK/DgDHw7uk4k0AYzREPr/8STCPeEVrWz78EDKeCXuVUP
XQAKBEUjNnmMJgMm5wjyc9k148xZ+3kNYDCCZnmD4HuK90e9wst79jxjrkIyyuIK
Wpa+uxhJmdWIAvCfi17HWAyOp9ewAeKJJ8T2PwT56UyQi3DaR3YHALGra8Z676yT
NHQ/is6TE92GnRictgrmahYO7qke8h39NzHhH6/21PwSeSv3VDw3nKmz+9qY6sZU
GXCCu+ngPdCCXtBWDRewEBO2MMJb2LJwELR6PhXsPHN29vpZtfd8VudSZLYSOuik
0/cSPVUCgYEA9WtKNDJB0Xg0vNRpAiv6DKPovERrcTTwPrWaQI9WWOtxgFKGniAo
p84atPsxXqnpojAp6XAF3o33uf2S0L3pH2afNck5DLNy0AA0Bc0LGIFwzEqfbTGr
c1cpU1jV4N/x6Icbx+NdqfKcgH74t63vZb+4UixSOMnbi5oiM6Qu3DcCgYEA8qRi
ZfWfjQhWn4XZKcIRAWsjV8I3D7JjWyQ7r8mo1h/aLZe3cAmyi9VgRtltuQpwrLrD
1kgNL/l9oRALJoN/hKhpTKzNWiHf0zSNknp/xWlDmik3ToZ0SSwuETR5lNSgT//a
3oJLN8PXaoUBXDcsJy9McK4iZmS8dQ270SW/ZF8CgYEA5xOlY64qcNu49E8frG7R
2tL+UT4u2AHbb4A4hC8yQzk0vnl1zS9EeHPEi8G0g4iCtjaZT/YtYJbVuOb8NNWL
yggrQk58C+xu31BBq3Cb0PAX0BM3N248G7bm71ZG05yovqNwUe5QA7OvDgH/l5sL
PQeeuqiGpnfR4wk2yN7/TFMCgYAXYWWl43wjT9lg97nMP0n6NAOs0icSGSNfxecG
ck0VjO4uFH91iUmuFbp4OT1MZkgjLL/wJvM2WzkSywP4CxW/h6bV35TOCZOSu26k
3a7wK8t60Fvm8ifEYUBzIfZRNAfajZHefPmYfwOD3RsbcqmLgRBBj1X7Pdu2/8LI
TXXaywKBgQCaXeEZ5BTuD7FvMSX95EamDJ/DMyE8TONwDHMIowf2IQbf0Y5U7ntK
6pm5O95cJ7l2m3jUbKIUy0Y8HPW2MgwstcZXKkzlR/IOoSVgdiAnPjVKlIUvVBUx
0u7GxCs5nfyEPjEHTBn1g7Z6U8c6x1r7F50WsLzJftLfqo7tElNO5A==
-----END RSA PRIVATE KEY-----
"""


CREDENTIALS = [
    (
        "Machine",
        {
            "username": fauxfactory.gen_alpha(),
            "password": fauxfactory.gen_alpha(),
            "privilage_escalation": "sudo",
            "privilage_escalation_username": fauxfactory.gen_alpha(),
            "privilage_escalation_password": fauxfactory.gen_alpha(),
        },
    ),
    ("Scm", {"username": fauxfactory.gen_alpha(), "password": fauxfactory.gen_alpha()}),
    (
        "Amazon",
        {
            "access_key": fauxfactory.gen_alpha(),
            "secret_key": fauxfactory.gen_alpha(),
            "sts_token": fauxfactory.gen_alpha(),
        },
    ),
    (
        "VMware",
        {
            "username": fauxfactory.gen_alpha(),
            "password": fauxfactory.gen_alpha(),
            "vcenter_host": fauxfactory.gen_alpha(),
        },
    ),
    (
        "OpenStack",
        {
            "username": fauxfactory.gen_alpha(),
            "password": fauxfactory.gen_alpha(),
            "authentication_url": fauxfactory.gen_alpha(),
            "project": fauxfactory.gen_alpha(),
            "domain": fauxfactory.gen_alpha(),
        },
    ),
    (
        "Red Hat Virtualization",
        {
            "username": fauxfactory.gen_alpha(),
            "password": fauxfactory.gen_alpha(),
            "host": fauxfactory.gen_alpha(),
        },
    ),
    (
        "Google Compute Engine",
        {
            "service_account": fauxfactory.gen_alpha(),
            "priv_key": private_key,
            "project": fauxfactory.gen_alpha(),
        },
    ),
]


@pytest.fixture(scope="module")
def action_collection(appliance):
    return appliance.collections.actions


@pytest.fixture(scope="module")
def credentials_collection(appliance):
    return appliance.collections.ansible_credentials


@pytest.mark.rhel_testing
@pytest.mark.tier(1)
def test_embedded_ansible_repository_crud(ansible_repository, wait_for_ansible):
    """
    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/12h
        tags: ansible_embed
    """
    updated_description = "edited_{}".format(fauxfactory.gen_alpha())
    with update(ansible_repository):
        ansible_repository.description = updated_description
    view = navigate_to(ansible_repository, "Edit")
    wait_for(lambda: view.description.value != "", delay=1, timeout=5)
    assert view.description.value == updated_description


@pytest.mark.rhel_testing
@pytest.mark.tier(1)
def test_embedded_ansible_repository_branch_crud(appliance, request, wait_for_ansible):
    """
    Ability to add repo with branch (without SCM credentials).

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/12h
        tags: ansible_embed
    """
    repositories = appliance.collections.ansible_repositories
    try:
        playbooks_yaml = cfme_data.ansible_links.playbook_repositories
        playbook_name = getattr(request, 'param', 'embedded_ansible')
        repository = repositories.create(
            name=fauxfactory.gen_alpha(),
            url=getattr(playbooks_yaml, playbook_name),
            description=fauxfactory.gen_alpha(),
            scm_branch="second_playbook_branch"
        )
    except (KeyError, AttributeError):
        message = "Missing ansible_links content in cfme_data, cannot setup repository"
        logger.exception(message)  # log the exception for debug of the missing content
        pytest.fail(message)

    request.addfinalizer(lambda: repository.delete_if_exists())

    view = navigate_to(repository, "Details")
    scm_branch = view.entities.summary("Repository Options").get_text_of("SCM Branch")
    assert scm_branch == repository.scm_branch

    repository.delete()
    assert not repository.exists


@pytest.mark.rhel_testing
@pytest.mark.tier(1)
def test_embedded_ansible_repository_invalid_url_crud(request, appliance, wait_for_ansible):
    """
    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    repositories = appliance.collections.ansible_repositories
    repository = repositories.create(
        name=fauxfactory.gen_alpha(),
        url='https://github.com/sbulage/invalid_repo_url.git',
        description=fauxfactory.gen_alpha())
    view = navigate_to(repository, "Details")
    assert view.entities.summary("Properties").get_text_of("Status") == "failed"

    repository.delete_if_exists()


@pytest.mark.rhel_testing
@pytest.mark.tier(1)
@pytest.mark.parametrize(("credential_type", "credentials"), CREDENTIALS,
    ids=[cred[0] for cred in CREDENTIALS])
def test_embedded_ansible_credential_crud(credentials_collection, wait_for_ansible, credential_type,
        credentials, appliance):
    """
    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    credential = credentials_collection.create(
        "{}_credential_{}".format(credential_type, fauxfactory.gen_alpha()),
        credential_type,
        **credentials
    )
    updated_value = "edited_{}".format(fauxfactory.gen_alpha())
    with update(credential):
        if credential.credential_type == "Google Compute Engine":
            credential.service_account = updated_value
        elif credential.credential_type == "Amazon":
            credential.access_key = updated_value
            # credential.username = updated_value
        else:
            credential.username = updated_value
            # credential.access_key = updated_value
    view = navigate_to(credential, "Details")

    def wait_for_changes(field_name):
        cr_opts = view.entities.summary("Credential Options")
        wait_for(
            lambda: cr_opts.get_text_of(field_name) == updated_value,
            fail_func=view.browser.selenium.refresh,
            delay=10,
            timeout=60,
        )

    if credential.credential_type == "Amazon":
        wait_for_changes("Access Key")
    elif credential.credential_type == "Google Compute Engine":
        wait_for_changes("Service Account Email Address")
    else:
        wait_for_changes("Username")
    credential.delete()


@pytest.mark.meta(blockers=[1437108])
@pytest.mark.tier(2)
def test_embed_tower_playbooks_list_changed(appliance, wait_for_ansible):
    """
    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    "Tests if playbooks list changed after playbooks repo removing"
    playbooks = []
    REPOSITORIES = [
        cfme_data.ansible_links.playbook_repositories.embedded_ansible,
        cfme_data.ansible_links.playbook_repositories.embedded_tower
    ]
    repositories_collection = appliance.collections.ansible_repositories
    for repo_url in REPOSITORIES:
        repository = repositories_collection.create(
            fauxfactory.gen_alpha(),
            repo_url,
            description=fauxfactory.gen_alpha()
        )
        playbooks.append(set(playbook.name for playbook in repository.playbooks.all()))
        repository.delete()
    assert not set(playbooks[1]).issuperset(set(playbooks[0]))


@pytest.mark.tier(2)
def test_control_crud_ansible_playbook_action(
    request, appliance, ansible_catalog_item, action_collection
):
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        initialEstimate: 1/12h
    """
    action = action_collection.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Run Ansible Playbook",
        action_values={
            "run_ansible_playbook": {
                "playbook_catalog_item": ansible_catalog_item.name,
                "inventory": {"target_machine": True},
            }
        },
    )

    @request.addfinalizer
    def _finalizer():
        if action.exists:
            appliance.rest_api.collections.actions.get(
                description=action.description
            ).action.delete()

    with update(action):
        ipaddr = fauxfactory.gen_ipaddr()
        new_descr = "edited_{}".format(fauxfactory.gen_alphanumeric())
        action.description = new_descr
        action.run_ansible_playbook = {
            "inventory": {
                "specific_hosts": True,
                "hosts": ipaddr
            },
        }
    view = navigate_to(action, "Edit")
    assert view.description.value == new_descr
    assert view.run_ansible_playbook.inventory.hosts.value == ipaddr
    view.cancel_button.click()
    action.delete()


@pytest.mark.tier(2)
def test_control_add_ansible_playbook_action_invalid_address(
    request, appliance, ansible_catalog_item, action_collection
):
    """
    Polarion:
        assignee: jdupuy
        casecomponent: Control
        initialEstimate: 1/12h
    """
    action = action_collection.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Run Ansible Playbook",
        action_values={
            "run_ansible_playbook": {
                "playbook_catalog_item": ansible_catalog_item.name,
                "inventory": {
                    "specific_hosts": True,
                    "hosts": "invalid_address_!@#$%^&*",
                },
            }
        },
    )

    @request.addfinalizer
    def _finalizer():
        if action.exists:
            appliance.rest_api.collections.actions.get(
                description=action.description
            ).action.delete()

    assert action.exists
    view = navigate_to(action, "Edit")
    assert view.run_ansible_playbook.inventory.hosts.value == "invalid_address_!@#$%^&*"
    view.cancel_button.click()


@pytest.mark.tier(2)
def test_embedded_ansible_credential_with_private_key(request, wait_for_ansible,
        credentials_collection):
    """Automation for BZ https://bugzilla.redhat.com/show_bug.cgi?id=1439589

    Adding new ssh credentials via Automation/Ansible/Credentials, add new credentials does not
    actually create new credentials with ssh keys.

    Bugzilla:
        1439589

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    credential = credentials_collection.create(
        fauxfactory.gen_alpha(),
        "Machine",
        username=fauxfactory.gen_alpha(),
        password=fauxfactory.gen_alpha(),
        private_key=private_key,
    )
    request.addfinalizer(credential.delete)
    assert credential.exists


@pytest.mark.tier(2)
def test_embedded_ansible_repository_playbook_link(ansible_repository):
    """
    Test clicking on playbooks cell from repository page and
    check it will navigate to the Playbooks area.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    view = navigate_to(ansible_repository, "Playbooks")
    # Asserting 'PlaybookRepositoryView' which is navigated from Repository to Playbooks view.
    # Playbooks view is coming from Repository view which is not existing Playbooks view.
    assert view.is_displayed
