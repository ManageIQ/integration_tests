import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.rest import ViaREST
from cfme.utils.appliance.implementations.ui import ViaUI

pytestmark = [test_requirements.auth, pytest.mark.manual]


@pytest.mark.tier(1)
def test_appliance_console_ipa():
    """
    Test setting up IPA authentication with invalid host settings

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/6h
    """
    pass


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
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(3)
def test_saml_verify_user_login():
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
        testSteps:
            1. Configure CFME for SAML with RHSSO server (cf. appliance.configure_saml)
            2. Try to login with SAML user
        expectedResults:
            1. Login to corporate account should redirect to RHSSO server
            2. User should be logged in with appropriate perms
    """
    pass


@pytest.mark.tier(2)
def test_saml_get_user_groups_from_ext_auth_httpd():
    """
    Enable “Get User Groups from External Authentication (httpd)” option.
    Verify “user groups from SAML server are updated correctly and user
    with correct groups can login. (retrieve groups option is not valid in
    case of SAML)

    Polarion:
        assignee: dgaikwad
        caseimportance: medium
        casecomponent: Auth
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.parametrize("mode", ["console", "ui"])
def test_verify_ui_reflects_ext_auth(mode):
    """
    Tests that login screen reflects external auth mode.

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        initialEstimate: 1/6h
        testSteps:
            1. Select external auth modes
            2. Disable the external auth modes
        expectedResults:
            1. Verify that the login screen UI reflects the auth mode
            2. Login screen goes back to normal
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1378213])
def test_ldap_group_lookup_error_message():
    """
    Polarion:
        assignee: dgaikwad
        caseimportance: low
        casecomponent: Auth
        caseposneg: negative
        initialEstimate: 1/4h
        testSteps:
            1. Configure appliance with LDAP server that has no memberOf overlay
            2. Perform user group lookup
        expectedResults:
            1.
            2. Error message saying no groups found for user should be displayed
    Bugzilla:
        1378213
    """
    pass


@pytest.mark.tier(2)
def test_verify_user_validation_authentication():
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: medium
        initialEstimate: 1/4h
        testSteps:
            1. Create user in ldap domain server.
            2. Do not assign any group to the user.
            3. Configure cfme for ldap
            4. Check audit.log and evm.log
            5. Check get users groups in UI
        expectedResults:
            1.
            2.
            3.
            4. logs should say “unable to match user"s group membership to an EVM role” message.
            5. should be disabled
    """
    pass


@pytest.mark.tier(2)
def test_verify_role_configuration_for_new_ldap_groups():
    """
    Retrieve ldap user groups, assign roles to the group.
    Login to cfme webui as ldap user and verify user role is working as
    expected.
    NOTE: execute rbac test cases.

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: medium
        initialEstimate: 1h
    """
    pass


@pytest.mark.tier(2)
def test_disable_local_login():
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        initialEstimate: 1/2h
        testSteps:
            1. Configure CFME for external auth
            2. Enable "Disable local login"
        expectedResults:
            1.
            2. Admin DB user should no longer be able to login
    """
    pass


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
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.tier(3)
def test_saml_login_fails_after_password_change():
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/4h
        setup:
            1. configure appliance with saml server
        testSteps:
            1. Create user and assign group in saml.
            2. Logout
            3. Change creds in SAML server
        expectedResults:
            1.
            2.
            3. SAML user should not be able to sign in
    """
    pass


@pytest.mark.tier(2)
def test_two_factor_auth_with_user_password_and_otp():
    """
    Polarion:
        assignee: dgaikwad
        initialEstimate: 1/3h
        casecomponent: Auth
        caseimportance: medium
    testSteps:
        1. configure CFME for external auth (IPA, SAML etc..)
        2. configure user for OTP in authentication server.
    expectedResults:
        1.
        2. verify two factor authentication for CFME works with user password
            and otp.
    """
    pass


@pytest.mark.tier(2)
def test_auth_mode_new_trusted_forest_table_entry():
    """
    verify the authentication mode is displayed correctly for new trusted
    forest table entry.

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(2)
def test_ldap_invalid_user_login():
    """
    Verifies scenarios associated with the invalid user login(negative
    test case).

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
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


@pytest.mark.tier(3)
def test_remove_display_name_for_user_in_ldap_and_verify_auth():
    """
    1. Remove display name for user in ldap and verify auth.

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
    """
    pass


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
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        initialEstimate: 1/2h
    """
    pass


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
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        initialEstimate: 1/2h
    """
    pass


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
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(2)
def test_verify_the_trusted_forest_settings_table_display_in_auth_page():
    """
    verify the trusted forest settings table display in authentication
    page. switch between the authentication modes and check the trusted
    forest settings table does not disappear.

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(3)
def test_external_auth_openldap_proxy_to_3_domains():
    """
    verify external authentication with OpenLDAP proxy to 3 different
    domains
    refer the bz: https://bugzilla.redhat.com/show_bug.cgi?id=1306436

    Bugzilla:
        1306436

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(2)
def test_appliance_console_ext_auth_options_skip():
    """
    Test skip update of ext_auth options through appliance_console

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
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


@pytest.mark.tier(2)
def test_multi_domain_configuration_for_external_auth_ldaps():
    """
    Look for the steps/instructions at
    https://mojo.redhat.com/docs/DOC-1085797
    Verify appliance_console is updated with “External Auth: “ correctly.
    Verify appliance_console displays all the domains configured. Now it
    displays only one. There will be BZ.

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        initialEstimate: 1/2h
    """
    pass


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
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: medium
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.tier(3)
def test_cfme_features_with_ldap():
    """
    verifies the cfme features with authentication mode configured to
    ldap.

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
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


@pytest.mark.tier(3)
def test_ldaps_customized_port():
    """
    Configure ldap/ldaps domain server with customized port.
    Configure cfme for customized domain ports. Check mojo page for
    details.
    Verify ldap user/group authentication.

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(3)
def test_saml_multiple_appliances_same_realm():
    """
    Verify configuring more than one appliance to SAML authentication as
    mentioned in Step#1 works fine.

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(2)
def test_session_timeout():
    """
    As admin change the session timeout in cfme webui.
    Login as ldap user and verify session times out after the specified
    timeout value.

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: low
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.meta(coverage=[1784145, 1805914])
@pytest.mark.parametrize("context", [ViaREST, ViaUI])
def test_openid_auth_provider(context):
    """
    Test setting up CFME with OpenID Auth Provider

    Bugzilla:
        1784145
        1805914

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: medium
        initialEstimate: 1/2h
        testSteps:
            1. Create client for appliance in keycloak server (rhsso73),
                - https://github.com/ManageIQ/manageiq_docs/blob/master/auth/openid_connect.adoc
                - NOTE: the "Client ID" cannot have "https://" in the string
                - Note: Set the root URL to "https://<FQDN of the appliance>", base URL as "/"
                - make note of the client secret in the "Credentials" tab of the client's details
            2. Create mappers (in keycloak) for client, "Client Host", "Client ID",
                "Client IP Address", "groups"
            3. Create OpenID test user and group if none available
            4. SSH into appliance and run:
                appliance_console_cli --oidc-config
                    --oidc-url=
                    <keycloak-server>:8080/auth/realms/CFME-OpenID/.well-known/openid-configuration
                    --oidc-client-id <appliance-fqdn>
                    --oidc-client-secret <client-secret>
            5. Login to appliance with OpenID user (clicking "Login to Corporate Account")
                via given context.
        expectedResults:
            1.
            2.
            3.
            4. Command should complete successfully
            5. User should be logged in with appropriate permissions
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1793532])
def test_login_self_service_ui():
    """
    Should be getting error on first attempt while clicked on login button without
    entering credentials on self service UI
    Bugzilla:
        1793532
    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseposneg: negative
        caseimportance: medium
        initialEstimate: 1/2h
        testSteps:
            1. Navigate to self service UI login page
            2. Click login without entering any creds
        expectedResults:
            1.
            2. Clicking the login button without entering credentials should have the
            error flash message appear immediately
    """
    pass
