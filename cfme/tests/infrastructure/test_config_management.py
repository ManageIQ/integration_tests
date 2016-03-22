
import fauxfactory
import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.configure.configuration import Category, Tag
from cfme.infrastructure.config_management import ConfigManager
from utils import error
from utils.update import update


@pytest.fixture
def config_manager_obj(cfme_data):
    """ Fixture that provides a random config manager (it doesn't set it up)"""
    cfg_mgr_key = fauxfactory.gen_choice(cfme_data['configuration_managers'].keys())
    return ConfigManager.load_from_yaml(cfg_mgr_key)


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


@pytest.mark.meta(blockers=["BZ#1244842"])
def test_config_manager_detail_config_btn(request, config_manager):
    sel.force_navigate('infrastructure_config_manager_refresh_detail',
        context={'manager': config_manager})


def test_config_manager_add(request, config_manager_obj):
    request.addfinalizer(config_manager_obj.delete)
    config_manager_obj.create()


def test_config_manager_add_invalid_url(request, config_manager_obj):
    request.addfinalizer(config_manager_obj.delete)
    config_manager_obj.url = "invalid_url"
    with error.expected('bad hostname'):
        config_manager_obj.create()


@pytest.mark.meta(blockers=["BZ#1319751"])
def test_config_manager_add_invalid_creds(request, config_manager_obj):
    request.addfinalizer(config_manager_obj.delete)
    config_manager_obj.credentials.principal = 'invalid_user'
    with error.expected('401'):
        config_manager_obj.create()


@pytest.mark.meta(blockers=["BZ#1244837"])
def test_config_manager_edit(request, config_manager):
    new_name = fauxfactory.gen_alpha(8)
    old_name = config_manager.name
    with update(config_manager):
        config_manager.name = new_name
    request.addfinalizer(lambda: config_manager.update(updates={'name': old_name}))
    assert (config_manager.name == new_name and config_manager.exists,
        "Failed to update configuration manager's name")


def test_config_manager_remove(config_manager):
    config_manager.delete()


def test_config_system_tag(request, config_system, tag):
    config_system.tag(tag)
    assert ('{}: {}'.format(tag.category.display_name, tag.display_name) in config_system.tags,
        "Failed to setup a configuration system's tag")


# def test_config_system_reprovision(config_system):
#    # TODO specify machine per stream in yamls or use mutex (by tagging/renaming)
#    pass
