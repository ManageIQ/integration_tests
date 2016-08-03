# -*- coding: utf-8 -*-
import pytest

from cfme.configure.access_control import Group, User
from cfme import Credential, login
from utils.conf import cfme_data
from utils.providers import setup_a_provider


@pytest.fixture(scope="module")
def setup_first_provider():
    setup_a_provider(validate=True, check_existing=True)


@pytest.fixture()
def group():
    data = cfme_data.get("openldap_test", {})
    if not data:
        pytest.skip("No openldap_test section in yaml")
    credentials = Credential(
        principal=data["username"],
        secret=data["password"],
    )
    return Group(description=data["group_name"], role="EvmRole-user",
                 user_to_lookup=data['username'], ldap_credentials=credentials)


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1357489])
@pytest.mark.parametrize(
    "add_from_ldap", [False, True],
    ids=['create', 'add_group_from_ldap_lookup'])
def test_openldap_auth(request, group, add_from_ldap, configure_openldap_auth_mode):
    data = cfme_data.get("openldap_test", {})
    if add_from_ldap:
        group.add_group_from_ldap_lookup()
    else:
        group.create()
    request.addfinalizer(group.delete)
    credentials = Credential(
        principal=data["username"],
        secret=data["password"],
        verify_secret=data["password"],
    )
    user = User(name=data["fullname"], credential=credentials)
    request.addfinalizer(user.delete)
    request.addfinalizer(login.login_admin)
    with user:
        login.login(user)
        assert login.current_full_name() == data["fullname"]
        login.logout()
    login.login_admin()
    assert user.exists is True
