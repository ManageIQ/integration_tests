import fauxfactory
import pytest

from cfme import test_requirements
from cfme.services.catalogs.ansible_catalog_item import AnsiblePlaybookCatalogItem
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update
from cfme.utils.version import current_version
from cfme.utils.wait import wait_for


REPOSITORIES = ["https://github.com/lcouzens/ansible_playbooks"]


@pytest.fixture(scope="module")
def wait_for_ansible(appliance):
    appliance.wait_for_embedded_ansible()


def test_embed_tower_UI_requests_notifications(appliance):
    """Add a repo and check websocket notification is displayed"""
    repositories = appliance.collections.ansible_repositories
    repository = repositories.create(
        'example',
        REPOSITORIES[0],
        description='example')
    view = navigate_to(repository, "Details")
    refresh = view.toolbar.refresh.click
    wait_for(
        lambda: view.entities.summary("Properties").get_text_of("Status") == "successful",
        timeout=60,
        fail_func=refresh
    )

    if repository.exists:
        repository.delete()


def test_embed_tower_UI_requests_notifications_negative(appliance):
    """Add a repo and check websocket notification is displayed"""
    repositories = appliance.collections.ansible_repositories
    repository = repositories.create(
        'example',
        REPOSITORIES[0],
        description='example')
    repository1 = repositories.create(
        'example',
        REPOSITORIES[0],
        description='example')


    if repository.exists:
        repository.delete()
