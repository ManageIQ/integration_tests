# -*- coding: utf-8 -*-
import pytest
from widgetastic_patternfly import CandidateNotFound

from cfme.base.credential import Credential
from cfme.utils.conf import cfme_data
from cfme.utils.log import logger

pytestmark = pytest.mark.uncollectif(lambda appliance: appliance.is_pod)

RETRIEVE_GROUP = 'retrieve_group'
CREATE_GROUP = 'create_group'


def pytest_generate_tests(metafunc):
    auth_modes = cfme_data.get('auth_test_data')
    if not auth_modes:
        return
    argvalues = [[authmode] for authmode in auth_modes]
    if 'configure_auth' in metafunc.fixturenames:
        metafunc.parametrize(['auth_mode'], argvalues)


@pytest.fixture()
def data(request, auth_mode, group_action):
    auth_data = cfme_data['auth_test_data'].get(auth_mode, {})
    if group_action == 'evm_default_group':
        auth_data['get_groups'] = False
    return auth_data


@pytest.fixture()
def group(request, data, auth_mode, group_action, appliance):
    if not data:
        pytest.skip("No data spcified for user group")
    credentials = Credential(
        principal=data["username"],
        secret=data["password"],
    )
    group_collection = appliance.collections.groups
    user_group = None
    if group_action == RETRIEVE_GROUP:
        user_group = group_collection.instantiate(
            description=data['group_name'], role="EvmRole-user",
            user_to_lookup=data["username"], ldap_credentials=credentials)
        if 'ext' in auth_mode:
            user_group.add_group_from_ext_auth_lookup()
        elif 'miq' in auth_mode:
            user_group.add_group_from_ldap_lookup()
        request.addfinalizer(user_group.delete)
    elif group_action == CREATE_GROUP:
        user_group = group_collection.create(
            description=data['group_name'], role="EvmRole-user",
            user_to_lookup=data["username"], ldap_credentials=credentials)
        request.addfinalizer(user_group.delete)


@pytest.fixture()
def user(request, data, group_action, appliance):
    if not data:
        pytest.skip("No data specified for user")
    username, password = data["username"], data["password"]
    if 'evm_default_group' in group_action:
        username, password = data['default_username'], data['default_password']
        data['fullname'] = data['default_userfullname']
    credentials = Credential(
        principal=username,
        secret=password,
        verify_secret=password,
    )
    user_obj = appliance.collections.users.instantiate(
        name=data['fullname'], credential=credentials
    )
    try:
        request.addfinalizer(user_obj.delete)
    except CandidateNotFound:
        logger.warning('User was not found during deletion')
    return user_obj


@pytest.mark.tier(1)
@pytest.mark.parametrize(
    "group_action", ['create_group', 'retrieve_group', 'evm_default_group'])
def test_auth_configure(appliance, request, configure_auth, group, user, data):
    """This test checks whether different cfme auth modes are working correctly.
       authmodes tested as part of this test: ext_ipa, ext_openldap, miq_openldap
       e.g. test_auth[ext-ipa_create-group]
        Prerequisities:
            * ``cfme_data.yaml`` file
        Steps:
            * Make sure corresponding auth_modes data is updated to ``cfme_data.yaml``
            * this test fetches the auth_modes from yaml and generates tests per auth_mode.
    """

    request.addfinalizer(appliance.server.login_admin)
    appliance.server.logout()
    with user:
        appliance.server.login(user)
        assert appliance.server.current_full_name() == data['fullname']
        appliance.server.logout()
    appliance.server.login_admin()
    assert user.exists is True
