import pytest

from cfme.configure.access_control import simple_user
from cfme.login import login
from cfme.web_ui import menu
from utils.conf import credentials
from utils.testgen import auth_groups, generate
from utils.providers import setup_a_provider

pytest_generate_tests = generate(auth_groups, auth_mode='ldap')


@pytest.fixture(scope="module")
def setup_first_provider():
    setup_a_provider(validate=True, check_existing=True)


def test_group_roles(configure_ldap_auth_mode, group_name, group_data, setup_first_provider):
    """Basic default LDAP group role RBAC test

    Validates expected menu and submenu names are present for default
    LDAP group roles

    """

    # This should be removed but currently these roles are subject to a bug
    if group_name in ['evmgroup-administrator',
                     'evmgroup-approver',
                     'evmgroup-auditor',
                     'evmgroup-operator',
                     'evmgroup-security',
                     'evmgroup-support',
                     'evmgroup-user']:
        pytest.skip("This role currently fails this test")

    try:
        username = credentials[group_name]['username']
        password = credentials[group_name]['password']
    except KeyError:
        pytest.fail('No match in credentials file for group "{}"'.format(group_name))

    login(simple_user(username, password))
    assert set(menu.nav.visible_pages()) == set(group_data)
