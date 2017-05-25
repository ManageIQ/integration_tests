# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from utils.wait import wait_for
from utils.update import update
from utils.version import current_version
from utils.appliance.implementations.ui import navigate_to
from cfme.ansible.repositories import RepositoryCollection
from cfme import test_requirements

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(server_roles=["+embedded_ansible"]),
    pytest.mark.uncollectif(current_version() < "5.8"),
    pytest.mark.ignore_stream("upstream"),
    test_requirements.ansible
]


@pytest.fixture(scope="module")
def embedded_ansible_role_enabled(appliance):

    def _wait_for_embedded_ansible():
        rc, _ = appliance.ssh_client.run_command("systemctl status supervisord")
        if rc == 0:
            return True
        else:
            return False

    wait_for(_wait_for_embedded_ansible, timeout="30m", delay=60,
        message="Embedded ansible role enabled.")


@pytest.mark.tier(1)
def test_embedded_ansible_repository_crud(embedded_ansible_role_enabled):
    repositories = RepositoryCollection()
    repository = repositories.create(
        fauxfactory.gen_alpha(),
        "https://github.com/quarckster/ansible_playbooks",
        description=fauxfactory.gen_alpha()
    )
    updated_description = "edited_{}".format(fauxfactory.gen_alpha())
    with update(repository):
        repository.description = updated_description
    view = navigate_to(repository, "Edit")
    wait_for(lambda: view.description.value != "", delay=1, timeout=5)
    assert view.description.value == updated_description
    repository.delete()
