# -*- coding: utf-8 -*-
import pytest
from fauxfactory import gen_alphanumeric

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.auth import ActiveDirectoryAuthProvider
from cfme.utils.auth import AmazonAuthProvider
from cfme.utils.auth import auth_user_data
from cfme.utils.auth import FreeIPAAuthProvider
from cfme.utils.auth import OpenLDAPAuthProvider
from cfme.utils.auth import OpenLDAPSAuthProvider
from cfme.utils.blockers import BZ
from cfme.utils.blockers import GH
from cfme.utils.conf import auth_data
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.uncollectif(lambda appliance: appliance.is_pod),
    pytest.mark.meta(blockers=[
        GH('ManageIQ/integration_tests:6465',
           # need SSL openldap server
           unblock=lambda auth_mode, prov_key: not (
               auth_mode in ['external', 'ldaps'] and
               auth_data.auth_providers[prov_key].type == 'openldaps')),
        BZ(1593171)]),  # 510z groups page doesn't load
    pytest.mark.usefixtures('prov_key', 'auth_mode', 'auth_provider', 'configure_auth', 'auth_user')
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
    argnames = ['auth_mode', 'prov_key', 'user_type', 'auth_user']
    argvalues = []
    idlist = []
    if 'auth_providers' not in auth_data:
        metafunc.parametrize(argnames, [
            pytest.param(
                None, None, None, None,
                marks=pytest.mark.uncollect("auth providers data missing"))])
        return
    # Holy nested loops, batman
    # go through each mode, then each auth type, and find auth providers matching that type
    # go through each user type for the given mode+auth_type (from param_maps above)
    # for each user type, find users in the yaml matching user_type an on the given auth provider
    # add parametrization for matching set of mode, auth_provider key, user_type, and user_dict
    # set id, use the username from userdict instead of an auto-generated "auth_user[\d]" ID
    for mode in test_param_maps.keys():
        for auth_type in test_param_maps.get(mode, {}):
            eligible_providers = {key: prov_dict
                                  for key, prov_dict in auth_data.auth_providers.items()
                                  if prov_dict.type == auth_type}
            for user_type in test_param_maps[mode][auth_type]['user_types']:
                for key, prov_dict in eligible_providers.items():
                    for user_dict in [u for u in auth_user_data(key, user_type) or []]:
                        if user_type in prov_dict.get('user_types', []):
                            argvalues.append((mode, key, user_type, user_dict))
                            idlist.append('-'.join([mode, key, user_type, user_dict.username]))
    metafunc.parametrize(argnames, argvalues, ids=idlist)


@pytest.fixture(scope='function')
def user_obj(appliance, auth_user, user_type):
    """return a simple user object, see if it exists and delete it on teardown"""
    # Replace spaces with dashes in UPN type usernames for login compatibility
    username = auth_user.username.replace(' ', '-') if user_type == 'upn' else auth_user.username
    user = appliance.collections.users.simple_user(
        username,
        credentials[auth_user.password].password,
        fullname=auth_user.fullname or auth_user.username)  # fullname could be empty
    yield user

    appliance.server.login_admin()
    if user.exists:
        user.delete()


@pytest.mark.rhel_testing
@pytest.mark.tier(1)
@pytest.mark.uncollectif(lambda auth_mode: auth_mode == 'amazon')  # default groups tested elsewhere
# this test only runs against users that have an evm built-in group
@pytest.mark.uncollectif(lambda auth_user: not any([True for g in auth_user.groups or []
                                                   if 'evmgroup' in g.lower()]),
                         reason='No evm group available for user')
def test_login_evm_group(appliance, auth_user, user_obj, soft_assert):
    """This test checks whether a user can login while assigned a default EVM group
        Prerequisities:
            * ``auth_data.yaml`` file
            * auth provider configured with user as a member of a group matching default EVM group
        Test will configure auth and login

    Polarion:
        assignee: apagac
        casecomponent: Auth
        initialEstimate: 1/4h
    """
    # get a list of groups for the user that match evm default group names
    # Replace spaces with dashes in UPN type usernames for login compatibility
    evm_group_names = [group for group in auth_user.groups if 'evmgroup' in group.lower()]
    with user_obj:
        logger.info('Logging in as user %s, member of groups %s', user_obj, evm_group_names)
        view = navigate_to(appliance.server, 'LoggedIn')
        assert view.is_displayed, 'user {} failed login'.format(user_obj)
        soft_assert(user_obj.name == view.current_fullname,
                    'user {} is not in view fullname'.format(user_obj))
        for name in evm_group_names:
            soft_assert(name in view.group_names,
                        'user {} evm group {} not in view group_names'.format(user_obj, name))

    # split loop to reduce number of logins
    appliance.server.login_admin()
    assert user_obj.exists, 'user record should have been created for "{}"'.format(user_obj)


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
@pytest.mark.uncollectif(lambda auth_user: not any([True for g in auth_user.groups or []
                                                   if 'evmgroup' not in g.lower()]),
                         reason='Only groups available for user are evm built-in')
def test_login_retrieve_group(appliance, request, auth_mode, auth_provider, soft_assert, auth_user,
                              user_obj):
    """This test checks whether different cfme auth modes are working correctly.
       authmodes tested as part of this test: ext_ipa, ext_openldap, miq_openldap
       e.g. test_auth[ext-ipa_create-group]
        Prerequisities:
            * ``auth_data.yaml`` file
        Steps:
            * Make sure corresponding auth_modes data is updated to ``auth_data.yaml``
            * this test fetches the auth_modes from yaml and generates tests per auth_mode.

    Polarion:
        assignee: apagac
        casecomponent: Auth
        initialEstimate: 1/4h
    """
    # get a list of (user_obj, groupname) tuples, creating the user object inline
    # filtering on those that do NOT evmgroup in groupname
    non_evm_group = [g for g in auth_user.groups or [] if 'evmgroup' not in g.lower()][0]
    # retrieving in test call and not fixture, getting the group from auth provider is part of test
    group = retrieve_group(appliance, auth_mode, auth_user.username, non_evm_group, auth_provider)

    with user_obj:
        view = navigate_to(appliance.server, 'LoggedIn')
        soft_assert(view.current_fullname == user_obj.name,
                    'user full name "{}" did not match UI display name "{}"'
                    .format(user_obj.name, view.current_fullname))
        soft_assert(group.description in view.group_names,
                    u'user group "{}" not displayed in UI groups list "{}"'
                    .format(group.description, view.group_names))

    appliance.server.login_admin()  # context should get us back to admin, just in case
    assert user_obj.exists, 'User record for "{}" should exist after login'.format(user_obj)

    @request.addfinalizer
    def _cleanup():
        if user_obj.exists:
            user_obj.delete()
        if group.exists:
            group.delete()


def format_user_principal(username, user_type, auth_provider):
    """Format CN/UID/UPN usernames for authentication with locally created groups"""
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
def local_group(appliance):
    """Helper method to check for existance of a group and delete if need be"""
    group_name = 'test-group-{}'.format(gen_alphanumeric(length=5))
    group = appliance.collections.groups.create(description=group_name, role='EvmRole-desktop')
    assert group.exists
    yield group

    if group.exists:
        group.delete()


@pytest.fixture(scope='function')
def local_user(appliance, auth_user, user_type, auth_provider, local_group):
    # list of created users, instantiating the Credential and formatting the user name in loop
    user = appliance.collections.users.create(
        name=auth_user.fullname or auth_user.username,  # fullname could be empty
        credential=Credential(
            principal=format_user_principal(auth_user.username, user_type, auth_provider),
            secret=credentials[auth_user.password].password),
        groups=[local_group])

    yield user

    if user.exists:
        user.delete()


@pytest.mark.tier(1)
@pytest.mark.uncollectif(lambda auth_mode: auth_mode == 'amazon',
                         'Amazon auth_data needed for local group testing')
def test_login_local_group(appliance, local_user, local_group, soft_assert):
    """
    Test remote authentication with a locally created group.
    Group is NOT retrieved from or matched to those on authentication provider


    Polarion:
        assignee: apagac
        initialEstimate: 1/4h
        casecomponent: Auth
    """
    # modify auth settings to not get groups
    appliance.server.authentication.auth_settings = {'auth_settings': {'get_groups': False}}

    with local_user:
        view = navigate_to(appliance.server, 'LoggedIn')
        soft_assert(view.current_fullname == local_user.name,
                    'user full name "{}" did not match UI display name "{}"'
                    .format(local_user.name, view.current_fullname))
        soft_assert(local_group.description in view.group_names,
                    'local group "{}" not displayed in UI groups list "{}"'
                    .format(local_group.description, view.group_names))


@pytest.mark.tier(1)
@pytest.mark.ignore_stream('5.8')
@pytest.mark.uncollectif(lambda auth_mode: auth_mode == 'amazon',
                         'Amazon auth_data needed for group switch testing')
@pytest.mark.uncollectif(lambda auth_user: len(auth_user.groups or []) < 2,
                         reason='User does not have multiple groups')
def test_user_group_switching(appliance, auth_user, auth_mode, auth_provider, soft_assert, request,
                              user_obj):
    """Test switching groups on a single user, between retreived group and built-in group

    Polarion:
        assignee: apagac
        initialEstimate: 1/4h
        casecomponent: Auth
    """
    retrieved_groups = []
    for group in auth_user.groups:
        # pick non-evm group when there are multiple groups for the user
        if 'evmgroup' not in group.lower():
            # create group in CFME via retrieve_group which looks it up on auth_provider
            logger.info(u'Retrieving a user group that is non evm built-in: {}'.format(group))
            retrieved_groups.append(retrieve_group(appliance,
                                                   auth_mode,
                                                   auth_user.username,
                                                   group,
                                                   auth_provider))
    else:
        logger.info('All user groups for group switching are evm built-in: {}'
                    .format(auth_user.groups))

    with user_obj:
        view = navigate_to(appliance.server, 'LoggedIn')
        # Check there are multiple groups displayed
        assert len(view.group_names) > 1, 'Only a single group is displayed for the user'
        display_other_groups = [g for g in view.group_names if g != view.current_groupname]
        # check the user name is displayed
        soft_assert(view.current_fullname == user_obj.name,
                    'user full name "{}" did not match UI display name "{}"'
                    .format(auth_user, view.current_fullname))
        # Not checking current group, determined by group priority
        # check retrieved groups are there
        for group in retrieved_groups:
            soft_assert(group.description in view.group_names,
                        u'user group "{}" not displayed in UI groups list "{}"'
                        .format(group, view.group_names))

        # change to the other groups
        for other_group in display_other_groups:
            soft_assert(other_group in auth_user.groups, u'Group {} in UI not expected for user {}'
                                                         .format(other_group, auth_user))
            view.change_group(other_group)
            assert view.is_displayed, (u'Not logged in after switching to group {} for {}'
                                       .format(other_group, auth_user))
            # assert selected group has changed
            soft_assert(other_group == view.current_groupname,
                        u'After switching to group {}, its not displayed as active'
                        .format(other_group))

    appliance.server.login_admin()
    assert user_obj.exists, 'User record for "{}" should exist after login'.format(auth_user)

    @request.addfinalizer
    def _cleanup():
        for group in retrieved_groups:
            if group.exists:
                group.delete()


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_ldap_password_plaintext():
    """
    Test that LDAP password is not logged in plaintext in evm.log.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(1)
def test_black_console_ipa_ntp():
    """
    Try to setup IPA on appliance when NTP daemon is stopped on server.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        caseposneg: negative
        setup:
            1. Have IPA server configured and running
                - https://mojo.redhat.com/docs/DOC-1058778
        testSteps:
            1. ssh into IPA server stop NTP daemon
            2. ssh to appliance and try to setup IPA
                - appliance_console_cli --ipaserver <IPA_URL> --ipaprincipal <LOGIN>
                    --ipapassword <PASS> --ipadomain <DOMAIN> --iparealm <REALM>
        expectedResults:
            1. NTP daemon stopped
            2. Command should fail; setting up IPA unsuccessful
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
@test_requirements.auth
def test_black_console_ipa():
    """
    Test setting up IPA authentication with invalid host settings

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_update_ldap_updates_login():
    """
    Change user/groups attribute in  ldap domain server.
    E.g change user display name
    Verify authentication fails for old display name
    Verify authentication for new display name for the user.
    Verify changing cache_credentials = True
    entry_cache_timeout = 600

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_saml_verify_user_login():
    """
    Create cfme default groups in saml server.
    Assign user to the default groups. e.g.  EvmGroup-administrator
    Configure cfme for ldaps external auth as in TC#1
    Authentication for ldap user is expected to be successful as cfme
    default groups are already assigned for user in saml server.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
        title: saml: verify user login with and without correct groups added to SAML server.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_black_console_ext_auth_options_enable():
    """
    Test enabling ext_auth options through appliance_console

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/6h
        setup:
            1. ssh to appliance
            2. run appliance_console
            3. select option "Update External Authentication Options"
            4. select each option to enable it
            5. select "Apply updates"
            6. check changes have been made
        startsin: 5.6
        testSteps:
            1. Enable Single Sign-On
            2. Enable SAML
            3. Enable Local Login
        expectedResults:
            1. check changes in ui
            2. check changes in ui
            3. check changes in ui
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(1)
def test_authentication_user_created_after_success_login():
    """
    Configure CFME for LDAP authentication and add group. Authenticate
    with LDAP user and check if user exists in Configuration - Access
    Control - Users.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_authentication_ldap_switch_groups():
    """
    Test whether user who is member of more LDAP groups is able to switch
    between them

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_external_auth_details_updated():
    """
    Run appliance_console and verify external_auth details are correctly
    updated for IPA

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        title: Verify external_auth details updated in appliance_console[IPA].
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_saml_sso():
    """
    Configure external auth as in TC#1 and enable SSO option.
    Verify SSO option works fine.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/4h
        title: Verify SAML SSO works fine, check both enable/disable options.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_ldap_group_lookup_error_message():
    """
    verify ldap group lookup fails with correct error message for invalid
    config details.
    1. configure ldap.
    2. specify wrong user details while group look up, verify group lookup
    fails with correct error message.
    refer the BZ:
    https://bugzilla.redhat.com/show_bug.cgi?id=1378213

    Polarion:
        assignee: apagac
        caseimportance: low
        casecomponent: Configuration
        caseposneg: negative
        initialEstimate: 1/4h
        title: verify ldap group lookup fails with correct error message
               for invalid user details
    Bugzilla:
        1378213
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_black_console_ext_auth_options_disable():
    """
    Test disabling ext_auth options through appliance_console

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/6h
        setup:
            1. ssh to appliance
            2. run appliance_console
            3. select option "Update External Authentication Options"
            4. select each option to enable it
            5. select "Apply updates"
            6. check changes have been made
        startsin: 5.6
        testSteps:
            1. Disable Single Sign-On
            2. Disable SAML
            3. Disable Local Login
        expectedResults:
            1. check changes in ui
            2. check changes in ui
            3. check changes in ui
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_look_up_ldap_groups():
    """
    verify Look Up LDAP Groups option works fine.
    1. configure external auth
    2. navigate to "configuration -> Access Control -> Groups -> Add new
    group"
    3. Check the option "Look Up LDAP Groups" and verify retrieve groups
    works fine.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/4h
        title: verify Look Up LDAP Groups option works fine.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_user_validation_authentication():
    """
    Create user in ldap domain server.
    Do not assign any group to the user.
    Configure cfme for ldaps external auth as in TC#1
    Validation for ldap user is expected to be successful but the
    authentication should fail as there is no group for the user.
    Check audit.log and evm.log for “unable to match user"s group
    membership to an EVM role” message.
    Verify this scenario by "Get User Groups from External Authentication
    (httpd)" option ENABLED and DISABLED.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        title: verify user validation works fine but authentication fails
               if no group is assigned for user.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_validate_lookup_button_provsioning():
    """
    configure ldap and validate for lookup button in provisioning form

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_role_configuration_for_new_ldap_groups():
    """
    Retrieve ldap user groups, assign roles to the group.
    Login to cfme webui as ldap user and verify user role is working as
    expected.
    NOTE: execute rbac test cases.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1h
        title: verify role configuration work as expected for new ldap groups
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_passwords_are_not_registered_in_plain_text_in_auth_logs():
    """
    verify passwords are not registered in plain text in auth logs.
    1. Configure LDAP/External Auth/Database Auth.
    2. Verify username and passwords are not registered in plain text to
    audit.log and evm.log

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        title: verify passwords are not registered in plain text in auth logs.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(1)
def test_ldap_user_login():
    """
    Verify the user login with valid credentials, based on role configured
    for the user.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/4h
        testSteps:
            1. login with the valid ldap user configured with CFME
            2. Verify the logged in user details in login page
            3. verify the feature access for the user based on the role
               configured/assigned to the user.
            4. verify the login with invalid credentials for the user login
        expectedResults:
            1. Login is expected to be successful for the valid user and credentials.
            2. username and group name needs be displayed.
            3. the user is expected to get full access to the features defined for his role.
            4. Login is expected to fail with invalid credentials.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_disable_local_login():
    """
    Configure external auth as in TC#1 and enable “disable local login.”
    Verify the default “admin” user for cfme no longer allowed to login to
    CFME
    ‘"disable local login". can be reset with an administratively
    privileged user and using the appliance_console "Update Ext Auth"
    option.
    Verify “admin” login works fine upon “disable local login” is
    disabled.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
        title: Verify disable local login option works fine. Verify enable/disable option
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_verify_ldap_user_login_when_email_has_an_apostrophe_character():
    """
    refer the BZ:
    https://bugzilla.redhat.com/show_bug.cgi?id=1379420

    Polarion:
        assignee: apagac
        caseimportance: low
        casecomponent: Configuration
        initialEstimate: 1/3h
        title: verify ldap user login when email has an apostrophe character

    Bugzilla:
        1379420
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_ldap_auth_without_groups():
    """
    verify LDAP authentication works without groups from LDAP
    refer this bz: https://bugzilla.redhat.com/show_bug.cgi?id=1302345
    Steps:
    1.In Configuration->Authentication, set the auth mode to LDAP.
    LDAP Hostname: "cfme-openldap-rhel7.cfme.lab.eng.rdu2.redhat.com"
    LDAP Port: 389
    UserType: Distinguished Name (UID=<user>)
    User Suffix: UID=<user> :  ou=people,ou=prod,dc=psavrocks,dc=com
    2. uncheck the "Get User Groups from LDAP"
    3. In Access Control -> Users, created new user
    "uid=test,ou=people,ou=prod,dc=psavrocks,dc=com" and set Group to
    EvmGroup-administrator
    ("uid=test,ou=people,ou=prod,dc=psavrocks,dc=com" user is already
    created in LDAP Server)
    4. Logout and tried Login with username: test and password: test,
    Login failed.
    Expected results:
    Base DN should always be visible and should be part of the LDAP
    Settings, when it is always needed.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/4h
        title: verify LDAP authentication works without groups from LDAP by
               uncheck the "Get User Groups from LDAP"
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_login_fails_after_password_change():
    """
    Configure SAML for cfme.
    Create user and assign group in saml.
    Create groups in cfme, and login and SAML user.
    Logout
    Change user credentials in SAML server.
    Verify user login  to CFME using old credential fails.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/4h
        title: Verify login fails for user in CFME after changing the
               Password in SAML for the user.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_two_factor_auth_with_user_password_and_otp():
    """
    Verifies two factor auth using external_authentication:
    Steps:
    1. configure CFME for external auth (IPA, SAML etc..)
    2. configure user for OTP in authentication server.
    3. verify two factor authentication for CFME works with user password
    and otp.

    Polarion:
        assignee: apagac
        initialEstimate: 1/3h
        casecomponent: Configuration
        caseimportance: medium
        title: verify two factor authentication works with user password and otp.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_auth_mode_new_trusted_forest_table_entry():
    """
    verify the authentication mode is displayed correctly for new trusted
    forest table entry.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/6h
        title: verify the authentication mode is displayed correctly for
               new trusted forest table entry.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(1)
def test_configure_ldap_authentication():
    """
    Verifies the ldap authentication mode configuration/setup on CFME
    appliance.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/4h
        testSteps:
            1. specify the authentication mode to LDAP.
            2. specify the valid credentials
            3. specify the port number, hostname and other details to
               configure the ldap authentication for CFME appliance.
        expectedResults:
            1. No Error is expected to occur by specifying the LDAP authentication mode.
            2. validation is expected to be successful with valid credentials
            3. the ldap authentication mode is expected to be successful
               after specifying the valid details.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_ldap_invalid_user_login():
    """
    Verifies scenario"s associated with the invalid user login(negative
    test case).

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/4h
        testSteps:
            1. login with the invalid user.
            2. configure the ldap with userA in groupA, configure CFME
               for userA and groupA. Login with userA
            3. delete the userA in the ldap. try Login with userA to CFME appliance
        expectedResults:
            1. login should fail for invalid credentials.
            2. login should be successful
            3. login should fail
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_remove_display_name_for_user_in_ldap_and_verify_auth():
    """
    1. Remove display name for user in ldap and verify auth.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
        title: Remove display name for user in ldap and verify auth.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_change_search_base():
    """
    Change the search base for user and groups lookup at domain component
    . e.g. change the search level from
    "ou=Groups,ou=prod,dc=qetest,dc=com "
    To "dc=qetest,dc=com"
    Change the ‘ldap_group_search_base’ and ‘ldap_user_search_base’ in
    /etc/sssd/sssd.conf for specific domain.
    Make sure domain_suffix is updated correctly for your ldap domain
    under test.
    Restart sssd service (service sssd restart)
    Verify configuration with dbus commands (refer MOJO)
    Verify user/group retrieval in CFME webui.
    user/group created at any hierarchy level under the tree
    dc=qetest,dc=com is expected to be retrieved.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
        title: Change the search base for user and groups lookup at domain component .
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_external_auth_with_sssd_single_domain():
    """
    Look for the steps/instructions at
    https://mojo.redhat.com/docs/DOC-1085797
    Verify appliance_console is updated with “External Auth: “ correctly

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/2h
        title: Configure External auth for ldaps with sssd.conf for single ldaps domain
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_change_domain_sequence_sssd_group_retrieval():
    """
    create user1 in test.com
    create group1 in test.com
    assign user1 to group1
    verify for the group retrived for user1
    Only group1 should be displayed in the group list in
    Note:  user should be authenticated with FQDN user1@test.com : group1
    test.com
    user1@qetest.com: qegroup1 qetest.com

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
        title: Change the domain sequence in sssd, and verify user groups retrieval.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_external_auth_configuration_with_ipa():
    """
    Set hostname for the appliance with FQDN
    Update /etc/hosts with IPA server ip and FQDN
    Update appliance FQDN to IPA server /etc/hosts
    Make sure, both the machine can communicate using FQDN.
    Run appliance_console and follow the steps in https://mojo.redhat.com/
    docs/DOC-1088176/edit?ID=1088176&draftID=1981816  Configuring CFME
    with external auth for IPA

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/4h
        title: External Auth configuration with IPA
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(1)
def test_retrieve_ldaps_groups():
    """
    Configure external auth as in TC#1
    Retrieve user groups in Access Control->groups->configuration->New
    group
    Monitor the audit.log and evm.log for no errors.
    validate the data comparing with ldap server data.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/4h
        title: verify retrieve ldaps groups works fine for ldap user from CFME webui.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_user_groups_can_be_retrieved_from_trusted_forest():
    """
    verify user groups can be retrieved from "trusted forest", when the
    "import roles from home forest" is unchecked.configuration:
    1. Create the user "ldaptest" and group "engineering" in ldap:"cfme-
    qe-ldap", and add "ldaptest" user to "engineering" group.
    2. Create the user "ldaptest" and group "cfme" in ldap:"cfme-qe-ipa"
    and add "ldaptest" user to "cfme" group.
    Steps :
    1. Login as "admin" and navigate to
    configure->configuration->authentication
    2. change the authentication mode to "ldap"
    3. specify the hostname for the "cfme-qe-ipa", as the primary ldap.
    4. in the "Role Settings" check "Get User Groups from LDAP", observe
    that "Trusted Forest Settings" table displayed below. specify "Base
    DN" and "Bind DN"
    5. click on "+" to add "Trusted Forest Settings", specify HostName as
    "cfme-qe-ldap",enter valid Base DN, Bind DN and "Bind Password" click
    add the trusted forest and click "Save"
    6. navigate to "access control"-> "groups"->"add new group", check
    (Look Up LDAP Groups), specify the user "ldaptest", click retrieve.
    Observe that only the groups(cfme) from Primary ldap (cfme-qe-ipa) are
    retrieved. no group(engineering) from "cfme-qe-ldap" is reqtrieved.
    7. manually add the group "engineering", logout and login as
    "ldaptest". Observe that login fails for the user "ldaptest"

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
        title: verify user groups can be retrieved from "trusted forest"
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_the_trusted_forest_settings_table_display_in_auth_page():
    """
    verify the trusted forest settings table display in authentication
    page. switch between the authentication modes and check the trusted
    forest settings table does not disappear.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/6h
        title: verify the trusted forest settings table display in authentication page.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_switch_groups_for_user_with_multiple_groups():
    """
    Assign ldap user to multiple default groups.
    Login as user and verify switch groups works fine.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        title: Verify switch groups works fine for user with multiple groups assigned.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_set_hostname_from_appliance_console_and_configure_external_auth():
    """
    set hostname from appliance_console and configure external_auth.
    Steps:
    1. ssh to appliance, and run appliance_console command
    2. change the appliance hostname with valid FQDN
    3. Verify External auth configuration does not fail.
    https://bugzilla.redhat.com/show_bug.cgi?id=1360928

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/3h
        title: set hostname from appliance_console and configure external_auth
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_ldap_group_retrieval_base64():
    """
    verify ldap group retrieval works fine for groups with descriptions
    which are base64 decoded , one random sample having an "é"
    Refer the BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1367600

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/4h
        title: verify ldap group retrieval works fine for groups with
               descriptions which are base64 decoded
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_authentication_user_not_in_ldap_but_in_db():
    """
    User is not able to authenticate if he has account in CFME DB but not
    in LDAP.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_verify_database_user_login_fails_with_external_auth_configured():
    """
    Login with user registered to cfme internal database.
    Authentication expected to fail, check audit.log and evm.log for
    correct log messages.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        title: Verify DataBase user login fails with External auth configured.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_external_auth_openldap_proxy_to_3_domains():
    """
    verify external authentication with OpenLDAP proxy to 3 different
    domains
    refer the bz: https://bugzilla.redhat.com/show_bug.cgi?id=1306436

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
        title: verify external authentication with OpenLDAP proxy to 3 different domains
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(1)
def test_auth_default_evm_groups_created():
    """
    Create cfme default groups in ldaps domain server.
    Assign user to the default groups. e.g.  EvmGroup-administrator
    Configure cfme for ldaps external auth as in TC#1
    Authentication for ldap user is expected to be successful as cfme
    default groups are already assigned for user in ldap server.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/4h
        title: verify user authentication works fine if default evm groups
               are already created and assigned for user in ldaps
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_saml_configuration_works_fine_for_cfme():
    """
    Look for the steps/instructions at http://file.rdu.redhat.com/abellott
    /manageiq_docs/master/auth/saml.html
    Verify appliance_console is updated with “External Auth: “ correctly

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/2h
        title: Verify SAML configuration works fine for CFME
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_black_console_ext_auth_options_skip():
    """
    Test skip update of ext_auth options through appliance_console

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/6h
        setup: -ssh to appliance
               -run appliance_console
               -select option "Update External Authentication Options"
               -select each option to enable it
               -select option
               1) Enable/Disable Single Sign-On
               2) Enable/Disable SAML
               3) Enable/Disable Local Login
               -select "Skip updates"
               -check changes have not been made
        startsin: 5.6
        testSteps:
            1. Enable Single Sign-On, SAML, Local Login then select skip updates
            2. Disable Single Sign-On, SAML, Local Login then select skip updates
            3. Enable Single Sign-On then select skip updates
            4. Disable Single Sign-On then select skip updates
            5. Enable SAML then select skip updates
            6. Disable SAML then select skip updates
            7. Enable Local Login then select skip updates
            8. Disable Local Login then select skip updates
        expectedResults:
            1. check changes in ui
            2. check changes in ui
            3. check changes in ui
            4. check changes in ui
            5. check changes in ui
            6. check changes in ui
            7. check changes in ui
            8. check changes in ui
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_multi_domain_configuration_for_external_auth_ldaps():
    """
    Look for the steps/instructions at
    https://mojo.redhat.com/docs/DOC-1085797
    Verify appliance_console is updated with “External Auth: “ correctly.
    Verify appliance_console displays all the domains configured. Now it
    displays only one. There will be BZ.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
        title: verify multi domain configuration for external auth ldaps
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_saml_get_user_groups_from_ext_auth_httpd():
    """
    Enable “Get User Groups from External Authentication (httpd)” option.
    Verify “user groups from SAML server are updated correctly and user
    with correct groups can login. (retrieve groups option is not valid in
    case of SAML)

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/2h
        title: saml: Verify “Get User Groups from External Authentication (httpd)” option.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_external_auth_config_for_ldap_appliance_console():
    """
    Run command “appliance_console”
    Select option for “configure external authentication”
    Verify “IPA Client already configured on this Appliance, Un-Configure
    first?” is displayed
    Answer yes to continue with unconfigure process.
    Verify Database user login works fine upon external auth un configured
    and auth mode set to ‘Database’.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/3h
        title: Verify external auth configuration for ldap can be un
               configured using appliance_console
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_cfme_features_with_ldap():
    """
    verifies the cfme features with authentication mode configured to
    ldap.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1h
        testSteps:
            1. login with ldap user
            2. verify the CFME features after login with ldap user.
        expectedResults:
            1. login should be successful
            2. All the CFME features should work properly with ldap authentication.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_black_console_ext_auth_options_all():
    """
    Test enabling/disabling all ext_auth options through appliance_console

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/6h
        setup: -ssh to appliance
               -run appliance_console
               -select option "Update External Authentication Options"
               -select each option to enable it
               -select option
               1) Enable/Disable Single Sign-On
               2) Enable/Disable SAML
               3) Enable/Disable Local Login
               -select "Apply updates"
               -check changes have been made
        startsin: 5.6
        testSteps:
            1. Enable Single Sign-On, SAML, Local Login
            2. Disable Single Sign-On, SAML, Local Login
        expectedResults:
            1. check changes in ui
            2. check changes in ui
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_ldaps_customized_port():
    """
    Configure ldap/ldaps domain server with customized port.
    Configure cfme for customized domain ports. Check mojo page for
    details.
    Verify ldap user/group authentication.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
        title: Configure  ldaps for customized port e.g 10636, 10389 and validate CFME auth
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(3)
def test_saml_multiple_appliances_same_realm():
    """
    Verify configuring more than one appliance to SAML authentication as
    mentioned in Step#1 works fine.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/2h
        title: saml: Verify multiple appliances can be added to the same REALM.
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_login_page_redirects_to_saml():
    """
    click on login to corporate account if local login is enabled,
    redirects to SAML REALM page for which user is appliance is configured
    to.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/4h
        title: Verify CFME login page redirects to SAML login page upon
               successful configuration
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_session_timeout():
    """
    As admin change the session timeout in cfme webui.
    Login as ldap user and verify session times out after the specified
    timeout value.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/6h
        title: Verify session timeout works fine for external auth.
    """
    pass
