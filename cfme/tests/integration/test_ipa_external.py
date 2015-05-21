# -*- coding: utf-8 -*-
import pytest

from cfme.configure.access_control import Group, User
from cfme import login
from utils.conf import cfme_data
from utils.providers import setup_a_provider

pytestmark = [pytest.mark.uncollect]


@pytest.fixture(scope="module")
def setup_first_provider():
    setup_a_provider(validate=True, check_existing=True)


@pytest.mark.ignore_stream("5.2")  # Old version can't do IPA
def test_external_auth_ipa(request, setup_first_provider, configure_external_auth_ipa_module):
    try:
        data = cfme_data.get("ipa_test", {})
    except KeyError:
        pytest.skip("No ipa_test section in yaml")
    group = Group(description='cfme', role="EvmRole-user")
    request.addfinalizer(group.delete)
    group.create()
    user = User(name=data["fullname"])
    request.addfinalizer(user.delete)
    request.addfinalizer(login.login_admin)
    login.login(data["username"], data["password"])
    assert login.current_full_name() == data["fullname"]
