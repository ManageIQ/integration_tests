# -*- coding: utf-8 -*-
import pytest

from cfme.configure.access_control import Group, User
from cfme.infrastructure.provider import InfraProvider
from cfme import login, Credential
from utils.conf import cfme_data
from utils.providers import setup_a_provider_by_class


@pytest.fixture(scope="module")
def setup_first_provider():
    setup_a_provider_by_class(InfraProvider)


def test_external_auth_ipa(request, configure_external_auth_ipa_module):
    try:
        data = cfme_data.get("ipa_test", {})
    except KeyError:
        pytest.skip("No ipa_test section in yaml")
    group = Group(description='cfme', role="EvmRole-user")
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
    login.login(user)
    assert login.current_full_name() == data["fullname"]
