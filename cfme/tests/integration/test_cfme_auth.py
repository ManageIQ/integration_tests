# -*- coding: utf-8 -*-
import pytest
from fauxfactory import gen_alphanumeric
from six import iteritems


from cfme.base.credential import Credential
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.auth import (
    OpenLDAPAuthProvider, OpenLDAPSAuthProvider, ActiveDirectoryAuthProvider, FreeIPAAuthProvider,
    AmazonAuthProvider
)
from cfme.utils.blockers import GH, BZ
from cfme.utils.conf import auth_data, credentials
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.uncollectif(lambda appliance: appliance.is_pod),
    pytest.mark.meta(blockers=[
        GH('ManageIQ/integration_tests:6465',
           # need SSL openldap server
           unblock=lambda auth_mode, prov_key: not (
               auth_mode in ['external', 'ldaps'] and
               auth_data.auth_providers[prov_key].type == 'openldaps')
           )
    ]),
    pytest.mark.usefixtures('prov_key', 'auth_mode', 'auth_provider', 'configure_auth')
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
    # TODO use supportability and provider type+version parametrization
    argnames = ['auth_mode', 'prov_key', 'user_type']
    argvalues = []
    if 'auth_providers' not in auth_data:
        metafunc.parametrize(argnames, [
            pytest.param(
                None, None, None,
                marks=pytest.mark.uncollect("auth providers data missing"))])
        return
    for mode in test_param_maps.keys():
        for auth_type in test_param_maps.get(mode, {}):
            eligible_providers = {key: prov_dict
                                  for key, prov_dict in iteritems(auth_data.auth_providers)
                                  if prov_dict.type == auth_type}
            for user_type in test_param_maps[mode][auth_type]['user_types']:
                argvalues.extend([(mode, key, user_type)
                                 for key, prov_dict in iteritems(eligible_providers)
                                 if user_type in prov_dict.get('user_types', [])])
    metafunc.parametrize(argnames, argvalues)


@pytest.mark.tier(1)
@pytest.mark.uncollectif(lambda auth_mode: auth_mode == 'amazon')  # default groups tested elsewhere
def test_login_evm_group(appliance, request, auth_user_data, user_type, soft_assert):
    """This test checks whether a user can login while assigned a default EVM group
        Prerequisities:
            * ``auth_data.yaml`` file
            * auth provider configured with user as a member of a group matching default EVM group
        Test will configure auth and login
    """
    # get a list of (user_obj, groupname) tuples, creating the user object inline
    # Replace spaces with dashes in UPN type usernames for login compatibility
    # filtering on those that have evmgroup in groupname
    user_tuples = []
    for user in auth_user_data:
        evm_matched_groups = [group for group in user.groups if 'evmgroup' in group.lower()]
        if evm_matched_groups:
            user_tuples.append(
                (appliance.collections.users.simple_user(
                    user.username.replace(' ', '-') if user_type == 'upn' else user.username,
                    credentials[user.password]['password'],
                    fullname=user.fullname),
                evm_matched_groups[0])
            )

    for user, groupname in user_tuples:
        with user:
            # use appliance.server methods for UI context instead of view directly
            navigate_to(appliance.server, 'LoggedIn', wait_for_view=True)
            display_name = appliance.server.current_full_name()
            display_groups = [name.lower() for name in appliance.server.group_names()]
            soft_assert(display_name == user.name,
                        'user full name "{}" did not match UI display name "{}"'
                        .format(user.name, display_name))
            soft_assert(groupname.lower() in display_groups,
                        'users group "{}" not displayed in UI groups list "{}"'
                        .format(groupname, display_groups))

    # split loop to reduce number of logins
    appliance.server.login_admin()
    for user, groupname in user_tuples:
        soft_assert(user.exists, 'user record should have been created for "{}"'.format(user))
        request.addfinalizer(user.delete)


def retrieve_group(appliance, auth_mode, username, groupname, auth_provider):
    """Retrieve group from ext/ldap auth provider through UI

    Args:
        appliance: appliance object
        auth_mode: key from cfme.configure.configuration.server_settings.AUTH_MODES, parametrization
        user_data: user_data AttrDict from yaml, with username, groupname, password fields

    """
    group = appliance.collections.groups.instantiate(
        description=groupname,
        role='EvmRole-user',
        user_to_lookup=username,
        ldap_credentials=Credential(principal=auth_provider.bind_dn,
                                    secret=auth_provider.bind_password))
    add_method = ('add_group_from_ext_auth_lookup'
                  if auth_mode == 'external' else
                  'add_group_from_ldap_lookup')
    if not group.exists:
        getattr(group, add_method)()  # call method to add
        wait_for(lambda: group.exists)
    else:
        logger.info('User Group exists, skipping create: %r', group)
    return group


@pytest.mark.tier(1)
@pytest.mark.uncollectif(lambda auth_mode: auth_mode == 'amazon')
def test_login_retrieve_group(appliance, request, auth_user_data, user_type, auth_mode,
                              auth_provider, soft_assert):
    """This test checks whether different cfme auth modes are working correctly.
       authmodes tested as part of this test: ext_ipa, ext_openldap, miq_openldap
       e.g. test_auth[ext-ipa_create-group]
        Prerequisities:
            * ``auth_data.yaml`` file
        Steps:
            * Make sure corresponding auth_modes data is updated to ``auth_data.yaml``
            * this test fetches the auth_modes from yaml and generates tests per auth_mode.
    """
    # get a list of (user_obj, groupname) tuples, creating the user object inline
    # Replace spaces with dashes in UPN type usernames for login compatibility
    # filtering on those that do NOT evmgroup in groupname
    user_group_tuples = [(
        appliance.collections.users.simple_user(
            user.username.replace(' ', '-') if user_type == 'upn' else user.username,
            credentials[user.password]['password'],
            fullname=user.fullname),
        retrieve_group(appliance, auth_mode, user.username, group, auth_provider))
        for user in auth_user_data
        for group in user.groups
        if 'evmgroup' not in group.lower()]  # exclude built-in evm groups

    logger.info('USER_GROUP_TUPLES: %r', user_group_tuples)

    for user, group in user_group_tuples:
        with user:
            navigate_to(appliance.server, 'LoggedIn', wait_for_view=True)
            display_name = appliance.server.current_full_name()
            display_groups = [name.lower() for name in appliance.server.group_names()]
            soft_assert(display_name == user.name,
                        'user full name "{}" did not match UI display name "{}"'
                        .format(user.name, display_name))
            soft_assert(group.description.lower() in display_groups,
                        'user group "{}" not displayed in UI groups list "{}"'
                        .format(group.description, display_groups))

    appliance.server.login_admin()
    for user, group in user_group_tuples:
        soft_assert(user.exists, 'User record for "{}" should exist after login'.format(user))

    @request.addfinalizer
    def _cleanup():
        for user, group in user_group_tuples:
            if user.exists:
                user.delete()
            if group.exists:
                group.delete()


@pytest.fixture(scope='function')
def local_group(appliance):
    """Helper method to check for existance of a group and delete if need be"""
    group_collection = appliance.collections.groups
    group_args = {
        'description': 'test-group-{}'.format(gen_alphanumeric(length=5)),
        'role': 'EvmRole-desktop'}
    group = group_collection.create(**group_args)  # gets re-instantiated in create
    assert group.exists
    yield group

    if group.exists:
        group.delete()


def format_user_principal(username, user_type, auth_provider):
    """Format CN/UID/UPN usernames for authentication"""
    if user_type == 'upn':
        return '{}@{}'.format(username.replace(' ', '-'),
                              auth_provider.user_types[user_type].user_suffix)
    elif user_type in ['uid', 'cn']:
        return '{}={},{}'.format(user_type,
                                 username,
                                 auth_provider.user_types[user_type].user_suffix)
    else:
        pytest.skip('No user formatting for {} and user type {}'.format(auth_provider, user_type))


@pytest.fixture(scope='function')
def local_users(appliance, auth_user_data, user_type, auth_provider, local_group):
    users = [
        # list of created users, instantiating the Credential and formatting the user name in loop
        appliance.collections.users.create(
            name=user.fullname,
            credential=Credential(
                principal=format_user_principal(user.username, user_type, auth_provider),
                secret=credentials[user.password]['password']),
            groups=[local_group])
        for user in auth_user_data
    ]

    yield users

    for user in users:
        if user.exists:
            user.delete()


@pytest.mark.tier(1)
@pytest.mark.meta(blockers=[BZ(1538791, forced_streams=['5.8'])])  # username field too short
@pytest.mark.uncollectif(lambda auth_mode: auth_mode == 'amazon',
                         'Amazon auth_data needed for local group testing')
def test_login_local_group(appliance, local_users, local_group, soft_assert):
    """
    Test remote authentication with a locally created group.
    Group is NOT retrieved from or matched to those on authentication provider

    """
    # modify auth settings to not get groups
    appliance.server.authentication.auth_settings = {'auth_settings': {'get_groups': False}}

    for user in local_users:
        with user:
            navigate_to(appliance.server, 'LoggedIn', wait_for_view=True)
            display_name = appliance.server.current_full_name()
            display_groups = [name.lower() for name in appliance.server.group_names()]
            soft_assert(display_name == user.name,
                        'user full name "{}" did not match UI display name "{}"'
                        .format(user.name, display_name))
            soft_assert(local_group.description.lower() in display_groups,
                        'local group "{}" not displayed in UI groups list "{}"'
                        .format(local_group.description, display_groups))
