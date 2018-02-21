# -*- coding: utf-8 -*-
import pytest
from six import iteritems

from cfme.base.credential import Credential
from cfme.utils.auth import (
    OpenLDAPAuthProvider, OpenLDAPSAuthProvider, ActiveDirectoryAuthProvider, FreeIPAAuthProvider,
    AmazonAuthProvider
)
from cfme.utils.blockers import GH
from cfme.utils.conf import auth_data
from cfme.utils.log import logger

pytestmark = [
    pytest.mark.uncollectif(lambda appliance: appliance.is_pod),
    pytest.mark.meta(blockers=[
        GH('ManageIQ/integration_tests:6465',
           # need SSL openldap server
           unblock=lambda auth_mode, prov_key: not (
               auth_mode in ['external', 'ldaps'] and
               auth_data.auth_providers[prov_key].type == 'openldaps')
           )
    ])
]

# map auth provider types, auth_modes, and user_types for test matrix
# first key level is auth mode
# second key level is provider type  (auth_provider key in parametrization)
# finally, user_types valid for testing on the above combination of provider+mode
test_param_maps = {
    'amazon': {
        AmazonAuthProvider.auth_type: {
            'user_types': ['username']}
    },
    'ldap': {
        ActiveDirectoryAuthProvider.auth_type: {
        # add cn_domain, samacct
            'user_types': ['cn', 'email', 'uid', 'upn']
        },
        FreeIPAAuthProvider.auth_type: {
            'user_types': ['cn', 'uid']  # add cn_domain
        },
        OpenLDAPAuthProvider.auth_type: {
            'user_types': ['cn', 'uid']  # add cn_domain
        }
    },
    'external': {
        FreeIPAAuthProvider.auth_type: {
            'user_types': ['uid']
        },
        OpenLDAPSAuthProvider.auth_type: {
            'user_types': ['uid']
        }
        # TODO add ActiveDirectory SAMAcct usertype for external
    }}


def pytest_generate_tests(metafunc):
    """ zipper auth_modes and auth_prov together and drop the nonsensical combos """
    argnames = ['auth_mode', 'prov_key', 'user_type']
    argvalues = []
    for mode in test_param_maps.keys():
        for auth_type in test_param_maps.get(mode, {}):
            eligible_providers = {key:prov_dict
                                  for key, prov_dict in iteritems(auth_data.auth_providers)
                                  if prov_dict.type == auth_type}
            for user_type in test_param_maps[mode][auth_type]['user_types']:
                argvalues.extend([[mode, key, user_type]
                                 for key, prov_dict in iteritems(eligible_providers)
                                 if user_type in prov_dict.get('user_types', [])])
    metafunc.parametrize(argnames, argvalues)


@pytest.yield_fixture(scope='function')
def create_group(appliance, **kwargs):
    """Helper method to check for existance of a group and delete if need be"""
    group_collection = appliance.collections.groups
    group_args = {
        'description': kwargs.get('group_name'),
        'role': kwargs.get('role')}
    group = group_collection.create(**group_args)  # gets re-instantiated in create
    assert group.exists
    yield group

    try:
        group.delete()
    except Exception:
        logger.warning('Exception during group fixture cleanup')


@pytest.yield_fixture(scope='function')
def retrieve_group(data, appliance, auth_mode):
    if not data:
        pytest.skip("No data spcified for user group")
    credentials = Credential(
        principal=data["username"],
        secret=data["password"],
    )
    group_collection = appliance.collections.groups
    user_group = group_collection.instantiate(
        description=data['group_name'], role="EvmRole-user",
        user_to_lookup=data["username"], ldap_credentials=credentials)
    if auth_mode == 'external':
        user_group.add_group_from_ext_auth_lookup()
    else:
        user_group.add_group_from_ldap_lookup()

    yield user_group

    try:
        user_group.delete()
    except Exception:
        logger.warning('Exception during group fixture cleanup')


@pytest.mark.tier(1)
@pytest.mark.uncollectif(lambda auth_mode: auth_mode == 'amazon')  # default groups tested elsewhere
def test_login_evm_group(appliance, auth_mode, prov_key, user_type, auth_provider, configure_auth,
                         auth_user_data):
    """This test checks whether a user can login while assigned a default EVM group
        Prerequisities:
            * ``auth_data.yaml`` file
            * auth provider configured with user as a member of a group matching default EVM group
        Test will configure auth and login
    """
    coll = appliance.collections.users
    # get a list of (user_obj, groupname) tuples, filtering on those that have evmgroup in groupname
    user_tuples = [
        (coll.simple_user(user.username.replace(' ', '-') if user_type == 'upn' else user.username,
                          user.password, fullname=user.fullname),
         user.groupname)
        for user in auth_user_data
        if 'evmgroup' in user.groupname.lower()]

    for user, groupname in user_tuples:
        with user:
            # use appliance.server methods for UI context instead of view directly
            appliance.server.login(user, method='click_on_login')
            assert appliance.server.current_full_name() == user.name
            assert groupname.lower() in appliance.server.current_group_name().lower()

    # split loop to reduce number of logins
    appliance.server.login_admin()
    for user, groupname in user_tuples:
        assert user.exists


# @pytest.mark.tier(1)
# def test_login_create_group(appliance, request, auth_prov, auth_mode, configure_auth, prov_data,
#                             user_data, user):
#     """This test checks whether different cfme auth modes are working correctly.
#        authmodes tested as part of this test: ext_ipa, ext_openldap, miq_openldap
#        e.g. test_auth[ext-ipa_create-group]
#         Prerequisities:
#             * ``auth_data.yaml`` file
#         Steps:
#             * Make sure corresponding auth_modes data is updated to ``auth_data.yaml``
#             * this test fetches the auth_modes from yaml and generates tests per auth_mode.
#     """
#     credentials = Credential(principal=data.get('username'), secret=data.get('password'))
#     role = 'EvmRole-user'
#
#     request.addfinalizer(appliance.server.login_admin)
#     with user:
#         appliance.server.login(user, method='click_on_login')
#         assert appliance.server.current_full_name() == data['fullname']
#         appliance.server.logout()
#     appliance.server.login_admin()
#     assert user.exists is True
