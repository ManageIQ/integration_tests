import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.blockers import BZ
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(blockers=[BZ(1677548, forced_streams=["5.11"])]),
    test_requirements.ansible,
    test_requirements.tag,
]


@pytest.fixture(scope='module')
def credential(wait_for_ansible, appliance):
    credentials_collection = appliance.collections.ansible_credentials
    _credential = credentials_collection.create(
        fauxfactory.gen_alpha(18, start="Machine_Cred_"),
        'Machine',
        username=fauxfactory.gen_alpha(start="usr_"),
        password=fauxfactory.gen_alpha(start="pwd_")
    )
    wait_for(
        func=lambda: _credential.exists,
        message='credential appears on UI',
        fail_func=appliance.browser.widgetastic.refresh,
        delay=20,
        num_sec=240
    )

    yield _credential
    _credential.delete_if_exists()


@pytest.fixture(scope='module')
def playbook(appliance, ansible_repository):
    playbooks_collection = appliance.collections.ansible_playbooks
    return playbooks_collection.all()[0]


@pytest.fixture(scope='function')
def check_tag_place(soft_assert):

    def _check_tag_place(item, tag_place):
        tag = item.add_tag(details=tag_place)
        tags = item.get_tags()
        soft_assert(
            tag in tags,
            "{}: {} not in ({})".format(tag.category.display_name, tag.display_name, tags)
        )

        item.remove_tag(tag=tag, details=tag_place)
        tags = item.get_tags()
        soft_assert(
            tag not in tags,
            "{}: {} should not be in ({})".format(tag.category.display_name, tag.display_name, tags)
        )
    return _check_tag_place


@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_ansible_repository(ansible_repository, tag_place, check_tag_place):
    """ Test for cloud items tagging action from list and details pages

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Tagging
    """
    check_tag_place(ansible_repository, tag_place)


@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_ansible_credential(credential, tag_place, check_tag_place):
    """ Test for cloud items tagging action from list and details pages

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Tagging
    """
    check_tag_place(credential, tag_place)


@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'list'])
def test_tag_ansible_playbook(playbook, tag_place, check_tag_place):
    """ Test for cloud items tagging action from list and details pages

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Tagging
    """
    check_tag_place(playbook, tag_place)


@pytest.mark.meta(automates=[1526217])
@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_ansible_repository(ansible_repository, check_item_visibility, visibility):
    """ Test for cloud items tagging action from list and details pages

    Bugzilla:
        1526217

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Tagging
    """
    check_item_visibility(ansible_repository, visibility)


@pytest.mark.meta(automates=[1526219])
@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_ansible_credential(credential, check_item_visibility, visibility):
    """ Test for cloud items tagging action from list and details pages

    Bugzilla:
        1526219

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Tagging
    """
    check_item_visibility(credential, visibility)


@pytest.mark.meta(automates=[1526218])
@pytest.mark.parametrize('visibility', [True, False], ids=['visible', 'notVisible'])
def test_tagvis_playbook(playbook, check_item_visibility, visibility):
    """ Test for cloud items tagging action from list and details pages

    Bugzilla:
        1526218

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Tagging
    """
    check_item_visibility(playbook, visibility)


@pytest.mark.manual
@pytest.mark.tier(2)
def test_tagvis_tag_and_configuration_management_ansible_tower_job_templates():
    """
    Combination of My Company tag and ansible tower job template

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
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
        casecomponent: Ansible
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
        casecomponent: Ansible
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
