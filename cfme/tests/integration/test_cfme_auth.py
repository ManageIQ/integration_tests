# -*- coding: utf-8 -*-
import pytest

from cfme.configure.access_control import Group, User
from cfme import Credential, login
from utils import browser
from utils.conf import cfme_data

RETRIEVE_GROUP = 'retrieve_group'
CREATE_GROUP = 'create_group'


def pytest_generate_tests(metafunc):
    auth_modes = cfme_data['auth_test_data']
    argvalues = [[authmode] for authmode in auth_modes]
    if 'configure_auth' in metafunc.fixturenames:
        metafunc.parametrize(['auth_mode'], argvalues)


def auth_finalizer():
    browser.browser().refresh()
    login.login_admin()


@pytest.fixture()
def data(request, auth_mode, add_group):
    auth_data = cfme_data['auth_test_data'].get(auth_mode, {})
    if add_group == 'evm_default_group':
        auth_data['get_groups'] = False
    return auth_data


@pytest.fixture()
def group(request, data, auth_mode, add_group):
    if not data:
        pytest.skip("No data spcified for user group")
    credentials = Credential(
        principal=data["username"],
        secret=data["password"],
    )
    user_group = Group(description=data['group_name'], role="EvmRole-user",
                       user_to_lookup=data["username"], ldap_credentials=credentials)
    if add_group == RETRIEVE_GROUP:
        if 'ext' in auth_mode:
            user_group.add_group_from_ext_auth_lookup()
        elif 'miq' in auth_mode:
            user_group.add_group_from_ldap_lookup()
        request.addfinalizer(user_group.delete)
    elif add_group == CREATE_GROUP:
        user_group.create()
        request.addfinalizer(user_group.delete)


@pytest.fixture()
def user(request, data, add_group):
    if not data:
        pytest.skip("No data specified for user")
    username, password = data["username"], data["password"]
    if 'evm_default_group' in add_group:
        username, password = data['default_username'], data['default_password']
        data['fullname'] = data['default_userfullname']
    credentials = Credential(
        principal=username,
        secret=password,
        verify_secret=password,
    )
    user_obj = User(name=data['fullname'], credential=credentials)
    request.addfinalizer(user_obj.delete)
    return user_obj


@pytest.mark.tier(1)
@pytest.mark.parametrize(
    "add_group", ['create_group', 'retrieve_group', 'evm_default_group'])
def test_auth_configure(request, configure_auth, group, user, data):
    """This test checks whether different cfme auth modes are working correctly.
       authmodes tested as part of this test: ext_ipa, ext_openldap, miq_openldap
       e.g. test_auth[ext-ipa_create-group]
        Prerequisities:
            * ``cfme_data.yaml`` file
        Steps:
            * Make sure corresponding auth_modes data is updated to ``cfme_data.yaml``
            * this test fetches the auth_modes from yaml and generates tests per auth_mode.
    """
    request.addfinalizer(auth_finalizer)
    with user:
        login.login(user, submit_method='click_on_login')
        assert login.current_full_name() == data['fullname']
        login.logout()
    login.login_admin()
    assert user.exists is True
