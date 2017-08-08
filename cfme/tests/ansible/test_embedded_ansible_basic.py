# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.ansible.repositories import RepositoryCollection
from cfme.ansible.credentials import CredentialsCollection
from utils.appliance.implementations.ui import navigate_to
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


@pytest.fixture(scope="module")
def wait_for_ansible(appliance):
    appliance.wait_for_embedded_ansible()


@pytest.mark.tier(1)
def test_embedded_ansible_repository_crud(request, wait_for_ansible):
    repositories = RepositoryCollection()
    repository = repositories.create(
        fauxfactory.gen_alpha(),
        "https://github.com/quarckster/ansible_playbooks",
        description=fauxfactory.gen_alpha()
    )

    @request.addfinalizer
    def _delete_if_exists():
        if repository.exists:
            repository.delete()

    updated_description = "edited_{}".format(fauxfactory.gen_alpha())
    with update(repository):
        repository.description = updated_description
    view = navigate_to(repository, "Edit")
    wait_for(lambda: view.description.value != "", delay=1, timeout=5)
    assert view.description.value == updated_description
    repository.delete()


@pytest.mark.tier(1)
@pytest.mark.parametrize(("credential_type", "credentials"), CREDENTIALS,
    ids=[cred[0] for cred in CREDENTIALS])
def test_embedded_ansible_credential_crud(request, wait_for_ansible, credential_type, credentials):
    credentials_collection = CredentialsCollection()
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
