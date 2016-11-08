import fauxfactory
import pytest
from cfme.configure.configuration import Category, Tag
from utils import error, version
from utils.update import update
from utils.testgen import config_managers, generate
from utils.blockers import BZ


pytest_generate_tests = generate(config_managers)
# TODO
# Investigate why this does not work
# pytestmark = pytest.mark.uncollectif(lambda config_manager_obj: config_manager_obj.type ==
#             "Ansible Tower" and version.current_version() < "5.6")


@pytest.yield_fixture
def config_manager(config_manager_obj):
    """ Fixture that provides a random config manager and sets it up"""
    config_manager_obj.create()
    yield config_manager_obj
    config_manager_obj.delete()


@pytest.fixture
def config_system(config_manager):
    return fauxfactory.gen_choice(config_manager.systems)


@pytest.yield_fixture(scope="module")
def category():
    cg = Category(name=fauxfactory.gen_alpha(8).lower(),
                  description=fauxfactory.gen_alphanumeric(length=32),
                  display_name=fauxfactory.gen_alphanumeric(length=32))
    cg.create()
    yield cg
    cg.delete()


@pytest.yield_fixture(scope="module")
def tag(category):
    tag = Tag(name=fauxfactory.gen_alpha(8).lower(),
              display_name=fauxfactory.gen_alphanumeric(length=32),
              category=category)
    tag.create()
    yield tag
    tag.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(
    blockers=[BZ(1388928, unblock=lambda config_manager_obj: (
        config_manager_obj.type == "Ansible Tower" and version.current_version() < "5.7.0.7") or
        config_manager_obj.type != "Ansible Tower")]
)
def test_config_manager_detail_config_btn(request, config_manager):
    config_manager.refresh_relationships()


@pytest.mark.tier(2)
@pytest.mark.meta(
    blockers=[BZ(1388928, unblock=lambda config_manager_obj: (
        config_manager_obj.type == "Ansible Tower" and version.current_version() < "5.7.0.7") or
        config_manager_obj.type != "Ansible Tower")]
)
def test_config_manager_add(request, config_manager_obj):
    request.addfinalizer(config_manager_obj.delete)
    config_manager_obj.create()


@pytest.mark.tier(3)
def test_config_manager_add_invalid_url(request, config_manager_obj):
    request.addfinalizer(config_manager_obj.delete)
    config_manager_obj.url = "invalid_url"
    if config_manager_obj.type == "Ansible Tower":
        error_message = 'getaddrinfo: Name or service not known'
    else:
        # BZ about bad text is raised 1382671
        error_message = 'Could not load data from invalid_url - is your server down? - was ' \
                        'rake apipie:cache run when using apipie cache? ' \
                        '(typical production settings)'

    with error.expected(error_message):
        config_manager_obj.create()


@pytest.mark.tier(3)
def test_config_manager_add_invalid_creds(request, config_manager_obj):
    request.addfinalizer(config_manager_obj.delete)
    config_manager_obj.credentials.principal = 'invalid_user'
    with error.expected('Invalid username/password'):
        config_manager_obj.create()


@pytest.mark.tier(3)
@pytest.mark.meta(
    blockers=[BZ(1388928, unblock=lambda config_manager_obj: (
        config_manager_obj.type == "Ansible Tower" and version.current_version() < "5.7.0.7") or
        config_manager_obj.type != "Ansible Tower")]
)
def test_config_manager_edit(request, config_manager):
    new_name = fauxfactory.gen_alpha(8)
    old_name = config_manager.name
    with update(config_manager):
        config_manager.name = new_name
    request.addfinalizer(lambda: config_manager.update(updates={'name': old_name}))
    assert (config_manager.name == new_name and config_manager.exists),\
        "Failed to update configuration manager's name"


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda config_manager_obj: config_manager_obj.type == "Ansible Tower" and
    version.current_version() > "5.7.0.6")
@pytest.mark.meta(
    blockers=[BZ(1388928, unblock=lambda config_manager_obj: (
        config_manager_obj.type == "Ansible Tower" and version.current_version() < "5.7.0.7") or
        config_manager_obj.type != "Ansible Tower")]
)
def test_config_manager_remove(config_manager):
    config_manager.delete()


# Disable this test for Tower, no Configuration profiles can be retrieved from Tower side yet
@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda config_manager_obj: config_manager_obj.type == "Ansible Tower")
@pytest.mark.meta(
    blockers=[BZ(1388928, unblock=lambda config_manager_obj: (
        config_manager_obj.type == "Ansible Tower" and version.current_version() < "5.7.0.7") or
        config_manager_obj.type != "Ansible Tower")]
)
def test_config_system_tag(request, config_system, tag):
    config_system.tag(tag)
    assert '{}: {}'.format(tag.category.display_name, tag.display_name) in config_system.tags,\
        "Failed to setup a configuration system's tag"


# def test_config_system_reprovision(config_system):
#    # TODO specify machine per stream in yamls or use mutex (by tagging/renaming)
#    pass
