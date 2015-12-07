import pytest
import cfme.configure.access_control as ac
import fauxfactory
from cfme import Credential, login
from utils import menu_plugin as mp
from cfme.fixtures import pytest_selenium as sel
from utils.providers import setup_a_provider


@pytest.fixture(scope="module")
def setup_infra_provider():
    return setup_a_provider(prov_class="infra", validate=True, check_existing=True,
        required_keys=['ownership_vm'])


@pytest.fixture(scope="module")
def setup_menu_plugin():
    mp.menu_plugin_setup()


@pytest.yield_fixture(scope="module")
def new_role():
    role = ac.Role(name='role_' + fauxfactory.gen_alphanumeric())
    role.create()
    yield role
    login.login_admin()
    role.delete()


@pytest.yield_fixture(scope="module")
def new_group(new_role):
    group = ac.Group(description='group_' + fauxfactory.gen_alphanumeric(),
        role=new_role.name)
    group.create()
    yield group
    login.login_admin()
    group.delete()


def new_credential():
    return Credential(principal='uid' + fauxfactory.gen_alphanumeric(), secret='redhat')


@pytest.yield_fixture(scope="module")
def non_admin_user(new_group):
    user1 = ac.User(name='user_' + fauxfactory.gen_alphanumeric(),
                credential=new_credential(),
                email='abc@redhat.com',
                group=new_group,
                cost_center='Workload',
                value_assign='Database')
    user1.create()
    yield user1
    login.login_admin()
    user1.delete()


@pytest.mark.meta(blockers=["BZ#1286627"])
def test_default_module(setup_menu_plugin):
    # Click Redhat Homepage link
    sel.force_navigate('rh_homepage')
    mp.menu_plugin_assert()
    # Click RedHat Course page link.
    sel.force_navigate('rh_courses')
    mp.menu_plugin_assert()


@pytest.mark.meta(blockers=["BZ#1286627"])
def test_non_admin_user_default_module(setup_infra_provider, setup_menu_plugin, non_admin_user):
    with non_admin_user:
        sel.force_navigate('rh_homepage')
        mp.menu_plugin_assert()
        # Click RedHat Course page link.
        sel.force_navigate('rh_courses')
        mp.menu_plugin_assert()


def test_teardown_menuplugin():
    mp.menu_plugin_teardown()
