# -*- coding: utf-8 -*-
import pytest

from cfme.configure.access_control import Group, User
from cfme import login
from utils.conf import cfme_data
from utils.providers import setup_a_provider


@pytest.fixture(scope="module")
def setup_first_provider():
    setup_a_provider(validate=True, check_existing=True)


def test_openldap_auth(request, setup_first_provider, configure_openldap_auth_mode):
    try:
        data = cfme_data.get("openldap_test", {})
    except KeyError:
        pytest.skip("No openldap_test section in yaml")
    group = Group(description='cfme', role="EvmRole-user")
    request.addfinalizer(group.delete)
    group.create()
    user = User(name=data["fullname"])
    request.addfinalizer(user.delete)
    request.addfinalizer(login.login_admin)
    login.login(data["username"], data["password"])
    assert login.current_full_name() == data["fullname"]
