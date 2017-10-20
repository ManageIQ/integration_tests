# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.services.catalogs.ansible_catalog_item import AnsiblePlaybookCatalogItem
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update
from cfme.utils.version import current_version
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(server_roles=["+embedded_ansible"]),
    pytest.mark.uncollectif(lambda: current_version() < "5.8"),
    pytest.mark.ignore_stream("upstream"),
    test_requirements.ansible
]


CREDENTIALS = [
    (
        "Machine",
        {
            "username": fauxfactory.gen_alpha(),
            "password": fauxfactory.gen_alpha(),
            "privilage_escalation": "sudo",
            "privilage_escalation_username": fauxfactory.gen_alpha(),
            "privilage_escalation_password": fauxfactory.gen_alpha(),
            "vault_password": fauxfactory.gen_alpha()
        }
    ),
    (
        "Scm",
        {
            "username": fauxfactory.gen_alpha(),
            "password": fauxfactory.gen_alpha(),
        }
    ),
    (
        "Amazon",
        {
            "access_key": fauxfactory.gen_alpha(),
            "secret_key": fauxfactory.gen_alpha(),
            "sts_token": fauxfactory.gen_alpha()
        }
    ),
    (
        "VMware",
        {
            "username": fauxfactory.gen_alpha(),
            "password": fauxfactory.gen_alpha(),
            "vcenter_host": fauxfactory.gen_alpha()
        }
    )
]

REPOSITORIES = [
    "https://github.com/quarckster/ansible_playbooks",
    "https://github.com/patchkez/ansible_playbooks"
]


@pytest.fixture(scope="module")
def wait_for_ansible(appliance):
    appliance.wait_for_embedded_ansible()


@pytest.fixture(scope="module")
def action_collection(appliance):
    return appliance.collections.actions


@pytest.yield_fixture(scope='module')
def ansible_repository(appliance):
    repositories = appliance.collections.ansible_repositories
    repository = repositories.create(
        fauxfactory.gen_alpha(),
        REPOSITORIES[0],
        description=fauxfactory.gen_alpha())

    yield repository

    if repository.exists:
        repository.delete()


@pytest.yield_fixture(scope="module")
def catalog_item(ansible_repository):
    cat_item = AnsiblePlaybookCatalogItem(
        fauxfactory.gen_alphanumeric(),
        fauxfactory.gen_alphanumeric(),
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

    if cat_item.exists:
        cat_item.delete()


@pytest.mark.tier(1)
def test_embedded_ansible_repository_crud(ansible_repository, wait_for_ansible):
    updated_description = "edited_{}".format(fauxfactory.gen_alpha())
    with update(ansible_repository):
        ansible_repository.description = updated_description
    view = navigate_to(ansible_repository, "Edit")
    wait_for(lambda: view.description.value != "", delay=1, timeout=5)
    assert view.description.value == updated_description


@pytest.mark.tier(1)
@pytest.mark.parametrize(("credential_type", "credentials"), CREDENTIALS,
    ids=[cred[0] for cred in CREDENTIALS])
def test_embedded_ansible_credential_crud(
        wait_for_ansible, credential_type, credentials, appliance):
    credentials_collection = appliance.collections.ansible_credentials
    credential = credentials_collection.create(
        "{}_credential_{}".format(credential_type, fauxfactory.gen_alpha()),
        credential_type,
        **credentials
    )
    updated_value = "edited_{}".format(fauxfactory.gen_alpha())
    with update(credential):
        if credential.credential_type != "Amazon":
            credential.username = updated_value
        else:
            credential.access_key = updated_value
    view = navigate_to(credential, "Details")

    def wait_for_changes(field_name):
        wait_for(
            lambda: view.credential_options.get_text_of(field_name) == updated_value,
            fail_func=view.browser.selenium.refresh,
            delay=10,
            timeout=60
        )

    if credential.credential_type == "Amazon":
        wait_for_changes("Access Key")
    else:
        wait_for_changes("Username")
    credential.delete()


@pytest.mark.meta(blockers=[1437108])
@pytest.mark.tier(2)
def test_embed_tower_playbooks_list_changed(appliance, wait_for_ansible):
    "Tests if playbooks list changed after playbooks repo removing"
    playbooks = []
    repositories_collection = appliance.collections.ansible_repositories
    for repo_url in REPOSITORIES:
        repository = repositories_collection.create(
            fauxfactory.gen_alpha(),
            repo_url,
            description=fauxfactory.gen_alpha()
        )
        playbooks.append(repository.playbooks.all())
        repository.delete()
    assert not set(playbooks[1]).issuperset(set(playbooks[0]))


@pytest.mark.tier(2)
def test_control_crud_ansible_playbook_action(request, catalog_item, action_collection):
    action = action_collection.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Run Ansible Playbook",
        action_values={
            "run_ansible_playbook":
            {
                "playbook_catalog_item": catalog_item.name,
                "inventory": {
                    "target_machine": True
                }
            }
        }
    )
    request.addfinalizer(action.delete_if_exists)
    with update(action):
        ipaddr = fauxfactory.gen_ipaddr()
        new_descr = "edited_{}".format(fauxfactory.gen_alphanumeric())
        action.description = new_descr
        action.run_ansible_playbook = {
            "inventory": {
                "specific_hosts": True,
                "hosts": ipaddr
            }
        }
    view = navigate_to(action, "Edit")
    assert view.description.value == new_descr
    assert view.run_ansible_playbook.inventory.hosts.value == ipaddr
    action.delete()


@pytest.mark.tier(2)
def test_control_add_ansible_playbook_action_invalid_address(request, catalog_item,
        action_collection):
    action = action_collection.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Run Ansible Playbook",
        action_values={
            "run_ansible_playbook":
            {
                "playbook_catalog_item": catalog_item.name,
                "inventory": {
                    "specific_hosts": True,
                    "hosts": "invalid_address_!@#$%^&*"
                }
            }
        }
    )
    request.addfinalizer(action.delete_if_exists)
    assert action.exists
    view = navigate_to(action, "Edit")
    assert view.run_ansible_playbook.inventory.hosts.value == "invalid_address_!@#$%^&*"
