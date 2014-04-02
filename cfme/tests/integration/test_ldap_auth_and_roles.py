import pytest

from cfme.login import force_login_user
from cfme.web_ui import menu
from utils.conf import credentials
from utils.testgen import auth_groups, generate

pytest_generate_tests = generate(auth_groups, auth_mode='ldap')


def test_group_roles(configure_ldap_auth_mode, group_name, group_data):
    """Basic default LDAP group role RBAC test

    Validates expected menu and submenu names are present for default
    LDAP group roles

    """
    try:
        username = credentials[group_name]['username']
        password = credentials[group_name]['password']
    except KeyError:
        pytest.fail('No match in credentials file for group "%s"' % group_name)

    force_login_user(username, password)
    assert menu.visible_pages() == group_data
