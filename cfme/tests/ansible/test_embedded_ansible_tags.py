import fauxfactory
import pytest

from widgetastic.exceptions import NoSuchElementException
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


@pytest.yield_fixture(scope='module')
def enabled_embedded_ansible(appliance):
    """Enables embedded ansible role"""
    appliance.server.settings.enable_server_roles("embedded_ansible")
    appliance.wait_for_embedded_ansible()
    yield
    appliance.server.settings.disable_server_roles("embedded_ansible")


@pytest.yield_fixture(scope='module')
def repository(appliance, enabled_embedded_ansible):
    repositories = appliance.collections.ansible_repositories
    repository = repositories.create(
        name=fauxfactory.gen_alpha(),
        url="https://github.com/quarckster/ansible_playbooks",
        description=fauxfactory.gen_alpha())
    view = navigate_to(repository, "Details")
    if appliance.version < "5.9":
        refresh = view.browser.refresh
    else:
        refresh = view.toolbar.refresh.click
    wait_for(
        lambda: view.entities.summary("Properties").get_text_of("Status") == "successful",
        timeout=60,
        fail_func=refresh
    )
    yield repository

    if repository.exists:
        repository.delete()


@pytest.yield_fixture(scope='module')
def credential(appliance, enabled_embedded_ansible):
    credentials_collection = appliance.collections.ansible_credentials
    view = navigate_to(appliance.server, 'AnsibleCredentials')
    try:
        credential = credentials_collection.instansiate(
            view.credentials[0]['Name'].text, view.credentials[0]['Type'].text)
    except NoSuchElementException:
        credential = credentials_collection.create(
            "{}_credential_{}".format('Machine', fauxfactory.gen_alpha()),
            'Machine',
            {
                "username": fauxfactory.gen_alpha(),
                "password": fauxfactory.gen_alpha(),
                "privilage_escalation": "sudo",
                "privilage_escalation_username": fauxfactory.gen_alpha(),
                "privilage_escalation_password": fauxfactory.gen_alpha()
            }
        )
    yield credential
    credential.delete()


@pytest.fixture(scope='module')
def playbook(appliance, repository):
    playbooks_collection = appliance.collections.ansible_playbooks
    return playbooks_collection.all()[0]


def check_tag_place(item, tag_place):
    tag = item.add_tag(details=tag_place)
    tags = item.get_tags()
    assert any(
        object_tags.category.display_name == tag.category.display_name and
        object_tags.display_name == tag.display_name for object_tags in tags), (
        "{}: {} not in ({})".format(tag.category.display_name, tag.display_name, str(tags)))

    item.remove_tag(tag=tag, details=tag_place)


@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_ansible_reposipory(repository, tag_place):
    """ Test for cloud items tagging action from list and details pages """
    check_tag_place(repository, tag_place)


@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_ansible_credential(credential, tag_place):
    """ Test for cloud items tagging action from list and details pages """
    check_tag_place(credential, tag_place)


@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_ansible_playbook(playbook, tag_place):
    """ Test for cloud items tagging action from list and details pages """
    check_tag_place(playbook, tag_place)


@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_ansible_reposipory(repository, check_item_visibility, visibility):
    """ Test for cloud items tagging action from list and details pages """
    check_item_visibility(repository, visibility)


@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_ansible_credential(credential, check_item_visibility, visibility):
    """ Test for cloud items tagging action from list and details pages """
    check_item_visibility(credential, visibility)


@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_playbook(playbook, check_item_visibility, visibility):
    """ Test for cloud items tagging action from list and details pages """
    check_item_visibility(playbook, visibility)
