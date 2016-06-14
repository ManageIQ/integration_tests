# -*- coding: utf-8 -*-
import pytest

from cfme.configure.access_control import Group, User
from cfme import Credential, login
from utils.conf import cfme_data
from utils.providers import setup_a_provider


@pytest.fixture(scope="module")
def setup_first_provider():
    setup_a_provider(validate=True, check_existing=True)


@pytest.mark.tier(3)
def test_openldap_auth(request, setup_first_provider, configure_openldap_auth_mode):
    data = cfme_data.get("openldap_test", {})
    if not data:
        pytest.skip("No openldap_test section in yaml")
    group = Group(description=data["group_name"], role="EvmRole-user")
    request.addfinalizer(group.delete)
    group.create()
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
