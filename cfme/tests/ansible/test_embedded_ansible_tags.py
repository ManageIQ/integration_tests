import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.ansible,
    pytest.mark.uncollectif(lambda appliance: appliance.version < "5.9",
                            reason="5.8 is not support tagging via UI"),
    pytest.mark.meta(blockers=[BZ(1640533, forced_streams=["5.10"])])
]


@pytest.fixture(scope='module')
def enabled_embedded_ansible(appliance):
    """Enables embedded ansible role"""
    appliance.server.settings.enable_server_roles("embedded_ansible")
    appliance.wait_for_embedded_ansible()
    yield
    appliance.server.settings.disable_server_roles("embedded_ansible")


@pytest.fixture(scope='module')
def repository(enabled_embedded_ansible, appliance):
    repositories = appliance.collections.ansible_repositories
    try:
        repository = repositories.create(
            name=fauxfactory.gen_alpha(),
            url=cfme_data.ansible_links.playbook_repositories.embedded_ansible,
            description=fauxfactory.gen_alpha())
    except KeyError:
        pytest.skip("Skipping since no such key found in yaml")
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


@pytest.fixture(scope='module')
def credential(enabled_embedded_ansible, appliance):
    credentials_collection = appliance.collections.ansible_credentials
    credential = credentials_collection.create(
        "{}_credential_{}".format('Machine', fauxfactory.gen_alpha()),
        'Machine',
        username=fauxfactory.gen_alpha(),
        password=fauxfactory.gen_alpha()
    )
    wait_for(
        func=lambda: credential.exists,
        message='credential appears on UI',
        fail_func=appliance.browser.widgetastic.refresh,
        delay=20,
        num_sec=240
    )

    yield credential
    if credential.exists:
        credential.delete()


@pytest.fixture(scope='module')
def playbook(appliance, repository):
    playbooks_collection = appliance.collections.ansible_playbooks
    return playbooks_collection.all()[0]


@pytest.fixture(scope='function')
def check_tag_place(soft_assert):

    def _check_tag_place(item, tag_place):
        tag = item.add_tag(details=tag_place)
        tags = item.get_tags()
        soft_assert(
            [object_tags if object_tags.category.display_name == tag.category.display_name and
             object_tags.display_name == tag.display_name else None for object_tags in tags], (
                "{}: {} not in ({})".format(tag.category.display_name, tag.display_name, str(tags)))
        )

        item.remove_tag(tag=tag, details=tag_place)
        tags = item.get_tags()
        soft_assert(
            not [object_tags if object_tags.category.display_name == tag.category.display_name and
                 object_tags.display_name == tag.display_name else None for object_tags in tags], (
                "{}: {} not in ({})".format(tag.category.display_name, tag.display_name, str(tags)))
        )
    return _check_tag_place


@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_ansible_repository(repository, tag_place, check_tag_place):
    """ Test for cloud items tagging action from list and details pages

    Polarion:
        assignee: anikifor
        initialEstimate: None
    """
    check_tag_place(repository, tag_place)


@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_ansible_credential(credential, tag_place, check_tag_place):
    """ Test for cloud items tagging action from list and details pages

    Polarion:
        assignee: anikifor
        initialEstimate: None
    """
    check_tag_place(credential, tag_place)


@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_ansible_playbook(playbook, tag_place, check_tag_place):
    """ Test for cloud items tagging action from list and details pages

    Polarion:
        assignee: anikifor
        initialEstimate: None
    """
    check_tag_place(playbook, tag_place)


@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_ansible_repository(repository, check_item_visibility, visibility):
    """ Test for cloud items tagging action from list and details pages

    Polarion:
        assignee: anikifor
        initialEstimate: None
    """
    check_item_visibility(repository, visibility)


@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_ansible_credential(credential, check_item_visibility, visibility):
    """ Test for cloud items tagging action from list and details pages

    Polarion:
        assignee: anikifor
        initialEstimate: None
    """
    check_item_visibility(credential, visibility)


@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_playbook(playbook, check_item_visibility, visibility):
    """ Test for cloud items tagging action from list and details pages

    Polarion:
        assignee: anikifor
        initialEstimate: None
    """
    check_item_visibility(playbook, visibility)


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_tag_and_configuration_management_ansible_tower_job_templates():
    """
    Combination of My Company tag and ansible tower job template

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_ansible_tower_tag_configured_system():
    """
    Polarion:
        assignee: anikifor
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/8h
        testSteps:
            1. Create group with tag, use this group for user creation
            2. Add tag(used in group) for Ansible Tower configured_system via
            detail page
            3. Remove tag for Ansible Tower configured_system via detail page
            4. Add tag for Ansible Tower configured_system via list
            5. Check Ansible Tower configured_system is visible for restricted
            user
            6. Remove tag for Ansible Tower configured_system via list
            7 . Check ansible tower configured_system isn"t visible for restricted
            user
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_ansible_tower_job():
    """
    Polarion:
        assignee: anikifor
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/8h
        testSteps:
            1. Create group with tag, use this group for user creation
            2. Add tag(used in group) for Ansible Tower job via detail page
            3. Remove tag for Ansible Tower job via detail page
            4. Add tag for Ansible Tower job via list
            5. Check Ansible Tower job is visible for restricted user
            6. Remove tag for Ansible Tower job via list
            7. Check ansible tower job isn"t visible for restricted user
    """
    pass
