import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.testgen import config_managers
from cfme.utils.testgen import generate
from cfme.utils.update import update


pytest_generate_tests = generate(gen_func=config_managers)
pytestmark = [
    pytest.mark.meta(blockers=[1491704]),
    pytest.mark.parametrize(
        config_manager_obj.type, [pytest.param('Ansible Tower', marks=test_requirements.tower),
        pytest.param('Red Hat Satellite', marks=test_requirements.satellite)]
    )
]


@pytest.fixture
def config_manager(config_manager_obj):
    """ Fixture that provides a random config manager and sets it up"""
    config_manager_obj.create()
    yield config_manager_obj
    config_manager_obj.delete()


@pytest.fixture
def config_system(config_manager):
    return fauxfactory.gen_choice(config_manager.systems)


@pytest.mark.tier(3)
def test_config_manager_detail_config_btn(request, config_manager):
    """
    Polarion:
        assignee: nachandr
        initialEstimate: 1/2h
        casecomponent: Ansible
    """
    config_manager.refresh_relationships()


@pytest.mark.tier(2)
def test_config_manager_add(request, config_manager_obj):
    """
    Polarion:
        assignee: nachandr
        casecomponent: Ansible
        initialEstimate: 1/4h
    """
    request.addfinalizer(config_manager_obj.delete)
    config_manager_obj.create()


@pytest.mark.tier(3)
def test_config_manager_add_invalid_url(request, config_manager_obj):
    """
    Polarion:
        assignee: nachandr
        initialEstimate: 1/15h
        casecomponent: Ansible
    """
    request.addfinalizer(config_manager_obj.delete)
    config_manager_obj.url = 'https://invalid_url'
    error_message = 'getaddrinfo: Name or service not known'
    with pytest.raises(Exception, match=error_message):
        config_manager_obj.create()


@pytest.mark.tier(3)
def test_config_manager_add_invalid_creds(request, config_manager_obj):
    """
    Polarion:
        assignee: nachandr
        caseimportance: medium
        initialEstimate: 1/4h
        casecomponent: Ansible
    """
    request.addfinalizer(config_manager_obj.delete)
    config_manager_obj.credentials.principal = 'invalid_user'
    if config_manager_obj.type == "Ansible Tower":
        msg = ('validation was not successful: {"detail":"Authentication credentials '
               'were not provided. To establish a login session, visit /api/login/."}')
    else:
        msg = 'Credential validation was not successful: 401 Unauthorized'
    with pytest.raises(Exception, match=msg):
        config_manager_obj.create()


@pytest.mark.tier(3)
def test_config_manager_edit(request, config_manager):
    """
    Polarion:
        assignee: nachandr
        initialEstimate: 1/15h
        casecomponent: Ansible
    """
    new_name = fauxfactory.gen_alpha(8)
    old_name = config_manager.name
    with update(config_manager):
        config_manager.name = new_name
    request.addfinalizer(lambda: config_manager.update(updates={'name': old_name}))
    assert (config_manager.name == new_name and config_manager.exists),\
        "Failed to update configuration manager's name"


@pytest.mark.tier(3)
def test_config_manager_remove(config_manager):
    """
    Polarion:
        assignee: nachandr
        initialEstimate: 1/15h
        casecomponent: Ansible
    """
    config_manager.delete()


# Disable this test for Tower, no Configuration profiles can be retrieved from Tower side yet
@pytest.mark.tier(3)
@test_requirements.tag
@pytest.mark.uncollectif(lambda config_manager_obj: config_manager_obj.type == "Ansible Tower")
def test_config_system_tag(request, config_system, tag, appliance):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Ansible
    """
    config_system.add_tag(tag=tag, details=False)
    assert tag in config_system.get_tags(), "Added tag not found on configuration system"


@pytest.mark.tier(3)
@test_requirements.tag
@pytest.mark.uncollectif(lambda config_manager_obj: config_manager_obj.type != "Ansible Tower")
def test_ansible_tower_job_templates_tag(request, config_manager, tag):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Ansible
        caseimportance: high

    Bugzilla:
        1673104
    """
    try:
        job_template = config_manager.appliance.collections.ansible_tower_job_templates.all()[0]
    except IndexError:
        pytest.skip("No job template was found")
    job_template.add_tag(tag=tag, details=False)
    request.addfinalizer(lambda: job_template.remove_tag(tag=tag))
    assert tag in job_template.get_tags(), "Added tag not found on configuration system"


# def test_config_system_reprovision(config_system):
#    # TODO specify machine per stream in yamls or use mutex (by tagging/renaming)
#    pass
