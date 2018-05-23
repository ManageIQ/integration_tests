import fauxfactory
import pytest
from cfme.configure.configuration.region_settings import Category, Tag
from cfme.utils.update import update
from cfme.utils.testgen import config_managers, generate


pytest_generate_tests = generate(gen_func=config_managers)
pytestmark = [pytest.mark.uncollectif(lambda config_manager_obj:
                                      config_manager_obj.type == "Ansible Tower"),
              pytest.mark.meta(blockers=[1491704])]


@pytest.fixture
def config_manager(config_manager_obj):
    """ Fixture that provides a random config manager and sets it up"""
    config_manager_obj.create()
    yield config_manager_obj
    config_manager_obj.delete()


@pytest.fixture
def config_system(config_manager):
    return fauxfactory.gen_choice(config_manager.systems)


@pytest.fixture(scope="module")
def category():
    cg = Category(name=fauxfactory.gen_alpha(8).lower(),
                  description=fauxfactory.gen_alphanumeric(length=32),
                  display_name=fauxfactory.gen_alphanumeric(length=32))
    cg.create()
    yield cg
    cg.delete()


@pytest.fixture(scope="module")
def tag(category):
    tag = Tag(name=fauxfactory.gen_alpha(8).lower(),
              display_name=fauxfactory.gen_alphanumeric(length=32),
              category=category)
    tag.create()
    yield tag
    tag.delete()


@pytest.mark.tier(3)
def test_config_manager_detail_config_btn(request, config_manager):
    """
    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/10h
    """
    config_manager.refresh_relationships()


@pytest.mark.tier(2)
def test_config_manager_add(request, config_manager_obj):
    """
    Polarion:
        assignee: pakotvan
        casecomponent: prov
        initialEstimate: 1/4h
    """
    request.addfinalizer(config_manager_obj.delete)
    config_manager_obj.create()


@pytest.mark.tier(3)
def test_config_manager_add_invalid_url(request, config_manager_obj):
    """
    Polarion:
        assignee: pakotvan
        caseimportance: low
        initialEstimate: 1/6h
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
        assignee: tpapaioa
        caseimportance: medium
        initialEstimate: 1/15h
    """
    request.addfinalizer(config_manager_obj.delete)
    config_manager_obj.credentials.principal = 'invalid_user'
    msg = 'Credential validation was not successful: 401 Unauthorized'
    with pytest.raises(Exception, match=msg):
        config_manager_obj.create()


@pytest.mark.tier(3)
def test_config_manager_edit(request, config_manager):
    """
    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/15h
    """
    new_name = fauxfactory.gen_alpha(8)
    old_name = config_manager.name
    with update(config_manager):
        config_manager.name = new_name
    request.addfinalizer(lambda: config_manager.update(updates={'name': old_name}))
    assert (config_manager.name == new_name and config_manager.exists),\
        "Failed to update configuration manager's name"


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda config_manager_obj: config_manager_obj.type == "Ansible Tower")
def test_config_manager_remove(config_manager):
    """
    Polarion:
        assignee: pakotvan
        caseimportance: low
        initialEstimate: 1/4h
    """
    config_manager.delete()


# Disable this test for Tower, no Configuration profiles can be retrieved from Tower side yet
@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda config_manager_obj: config_manager_obj.type == "Ansible Tower")
def test_config_system_tag(request, config_system, tag):
    """
    Polarion:
        assignee: rbabyuk
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/8h
    """
    config_system.add_tag(tag=tag, details=False)
    tags = config_system.get_tags()
    assert '{}: {}'.format(tag.category.display_name, tag.display_name) in \
        ['{}: {}'.format(t.category.display_name, t.display_name) for t in tags], \
        "Failed to setup a configuration system's tag"


@pytest.mark.tier(2)
# def test_config_system_reprovision(config_system):
#    # TODO specify machine per stream in yamls or use mutex (by tagging/renaming)
#    pass
