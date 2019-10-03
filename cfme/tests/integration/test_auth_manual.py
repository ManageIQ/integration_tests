import pytest


@pytest.mark.manual
@pytest.mark.tier(2)
def test_ldap_password_plaintext():
    """
    Test that LDAP password is not logged in plaintext in evm.log.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_black_console_ipa_ntp():
    """
    Try to setup IPA on appliance when NTP daemon is stopped on server.

    Polarion:
        assignee: jdupuy
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
def test_black_console_ipa():
    """
    Test setting up IPA authentication with invalid host settings

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
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
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_saml_verify_user_login():
    """
    Create cfme default groups in saml server.
    Assign user to the default groups. e.g.  EvmGroup-administrator
    Configure cfme for ldaps external auth as in TC#1
    Authentication for ldap user is expected to be successful as cfme
    default groups are already assigned for user in saml server.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
        title: saml: verify user login with and without correct groups added to SAML server.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_black_console_ext_auth_options_enable():
    """
    Test enabling ext_auth options through appliance_console

    Polarion:
        assignee: jdupuy
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
@pytest.mark.tier(1)
def test_authentication_user_created_after_success_login():
    """
    Configure CFME for LDAP authentication and add group. Authenticate
    with LDAP user and check if user exists in Configuration - Access
    Control - Users.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_authentication_ldap_switch_groups():
    """
    Test whether user who is member of more LDAP groups is able to switch
    between them

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_external_auth_details_updated():
    """
    Run appliance_console and verify external_auth details are correctly
    updated for IPA

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        title: Verify external_auth details updated in appliance_console[IPA].
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_verify_saml_sso():
    """
    Configure external auth as in TC#1 and enable SSO option.
    Verify SSO option works fine.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/4h
        title: Verify SAML SSO works fine, check both enable/disable options.
    """
    pass


@pytest.mark.manual
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
        assignee: jdupuy
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
@pytest.mark.tier(2)
def test_black_console_ext_auth_options_disable():
    """
    Test disabling ext_auth options through appliance_console

    Polarion:
        assignee: jdupuy
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
        assignee: jdupuy
        casecomponent: Configuration
        initialEstimate: 1/4h
        title: verify Look Up LDAP Groups option works fine.
    """
    pass


@pytest.mark.manual
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
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        title: verify user validation works fine but authentication fails
               if no group is assigned for user.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_validate_lookup_button_provsioning():
    """
    configure ldap and validate for lookup button in provisioning form

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_verify_role_configuration_for_new_ldap_groups():
    """
    Retrieve ldap user groups, assign roles to the group.
    Login to cfme webui as ldap user and verify user role is working as
    expected.
    NOTE: execute rbac test cases.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1h
        title: verify role configuration work as expected for new ldap groups
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_verify_passwords_are_not_registered_in_plain_text_in_auth_logs():
    """
    verify passwords are not registered in plain text in auth logs.
    1. Configure LDAP/External Auth/Database Auth.
    2. Verify username and passwords are not registered in plain text to
    audit.log and evm.log

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        title: verify passwords are not registered in plain text in auth logs.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_ldap_user_login():
    """
    Verify the user login with valid credentials, based on role configured
    for the user.

    Polarion:
        assignee: jdupuy
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
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
        title: Verify disable local login option works fine. Verify enable/disable option
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_verify_ldap_user_login_when_email_has_an_apostrophe_character():
    """
    refer the BZ:
    https://bugzilla.redhat.com/show_bug.cgi?id=1379420

    Polarion:
        assignee: jdupuy
        caseimportance: low
        casecomponent: Configuration
        initialEstimate: 1/3h
        title: verify ldap user login when email has an apostrophe character

    Bugzilla:
        1379420
    """
    pass


@pytest.mark.manual
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
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/4h
        title: verify LDAP authentication works without groups from LDAP by
               uncheck the "Get User Groups from LDAP"
    """
    pass


@pytest.mark.manual
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
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/4h
        title: Verify login fails for user in CFME after changing the
               Password in SAML for the user.
    """
    pass


@pytest.mark.manual
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
        assignee: jdupuy
        initialEstimate: 1/3h
        casecomponent: Configuration
        caseimportance: medium
        title: verify two factor authentication works with user password and otp.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_auth_mode_new_trusted_forest_table_entry():
    """
    verify the authentication mode is displayed correctly for new trusted
    forest table entry.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/6h
        title: verify the authentication mode is displayed correctly for
               new trusted forest table entry.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_configure_ldap_authentication():
    """
    Verifies the ldap authentication mode configuration/setup on CFME
    appliance.

    Polarion:
        assignee: jdupuy
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
@pytest.mark.tier(2)
def test_ldap_invalid_user_login():
    """
    Verifies scenario"s associated with the invalid user login(negative
    test case).

    Polarion:
        assignee: jdupuy
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
@pytest.mark.tier(3)
def test_remove_display_name_for_user_in_ldap_and_verify_auth():
    """
    1. Remove display name for user in ldap and verify auth.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
        title: Remove display name for user in ldap and verify auth.
    """
    pass


@pytest.mark.manual
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
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
        title: Change the search base for user and groups lookup at domain component .
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_external_auth_with_sssd_single_domain():
    """
    Look for the steps/instructions at
    https://mojo.redhat.com/docs/DOC-1085797
    Verify appliance_console is updated with “External Auth: “ correctly

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/2h
        title: Configure External auth for ldaps with sssd.conf for single ldaps domain
    """
    pass


@pytest.mark.manual
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
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
        title: Change the domain sequence in sssd, and verify user groups retrieval.
    """
    pass


@pytest.mark.manual
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
        assignee: jdupuy
        casecomponent: Configuration
        initialEstimate: 1/4h
        title: External Auth configuration with IPA
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_retrieve_ldaps_groups():
    """
    Configure external auth as in TC#1
    Retrieve user groups in Access Control->groups->configuration->New
    group
    Monitor the audit.log and evm.log for no errors.
    validate the data comparing with ldap server data.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        initialEstimate: 1/4h
        title: verify retrieve ldaps groups works fine for ldap user from CFME webui.
    """
    pass


@pytest.mark.manual
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
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
        title: verify user groups can be retrieved from "trusted forest"
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_verify_the_trusted_forest_settings_table_display_in_auth_page():
    """
    verify the trusted forest settings table display in authentication
    page. switch between the authentication modes and check the trusted
    forest settings table does not disappear.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/6h
        title: verify the trusted forest settings table display in authentication page.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_switch_groups_for_user_with_multiple_groups():
    """
    Assign ldap user to multiple default groups.
    Login as user and verify switch groups works fine.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        title: Verify switch groups works fine for user with multiple groups assigned.
    """
    pass


@pytest.mark.manual
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
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/3h
        title: set hostname from appliance_console and configure external_auth
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_ldap_group_retrieval_base64():
    """
    verify ldap group retrieval works fine for groups with descriptions
    which are base64 decoded , one random sample having an "é"
    Refer the BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1367600

    Polarion:
        assignee: jdupuy
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
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_verify_database_user_login_fails_with_external_auth_configured():
    """
    Login with user registered to cfme internal database.
    Authentication expected to fail, check audit.log and evm.log for
    correct log messages.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        title: Verify DataBase user login fails with External auth configured.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_external_auth_openldap_proxy_to_3_domains():
    """
    verify external authentication with OpenLDAP proxy to 3 different
    domains
    refer the bz: https://bugzilla.redhat.com/show_bug.cgi?id=1306436

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
        title: verify external authentication with OpenLDAP proxy to 3 different domains
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_auth_default_evm_groups_created():
    """
    Create cfme default groups in ldaps domain server.
    Assign user to the default groups. e.g.  EvmGroup-administrator
    Configure cfme for ldaps external auth as in TC#1
    Authentication for ldap user is expected to be successful as cfme
    default groups are already assigned for user in ldap server.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        initialEstimate: 1/4h
        title: verify user authentication works fine if default evm groups
               are already created and assigned for user in ldaps
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_saml_configuration_works_fine_for_cfme():
    """
    Look for the steps/instructions at http://file.rdu.redhat.com/abellott
    /manageiq_docs/master/auth/saml.html
    Verify appliance_console is updated with “External Auth: “ correctly

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        initialEstimate: 1/2h
        title: Verify SAML configuration works fine for CFME
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_black_console_ext_auth_options_skip():
    """
    Test skip update of ext_auth options through appliance_console

    Polarion:
        assignee: jdupuy
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
@pytest.mark.tier(2)
def test_multi_domain_configuration_for_external_auth_ldaps():
    """
    Look for the steps/instructions at
    https://mojo.redhat.com/docs/DOC-1085797
    Verify appliance_console is updated with “External Auth: “ correctly.
    Verify appliance_console displays all the domains configured. Now it
    displays only one. There will be BZ.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
        title: verify multi domain configuration for external auth ldaps
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_saml_get_user_groups_from_ext_auth_httpd():
    """
    Enable “Get User Groups from External Authentication (httpd)” option.
    Verify “user groups from SAML server are updated correctly and user
    with correct groups can login. (retrieve groups option is not valid in
    case of SAML)

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        initialEstimate: 1/2h
        title: saml: Verify “Get User Groups from External Authentication (httpd)” option.
    """
    pass


@pytest.mark.manual
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
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/3h
        title: Verify external auth configuration for ldap can be un
               configured using appliance_console
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_cfme_features_with_ldap():
    """
    verifies the cfme features with authentication mode configured to
    ldap.

    Polarion:
        assignee: jdupuy
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
@pytest.mark.tier(2)
def test_black_console_ext_auth_options_all():
    """
    Test enabling/disabling all ext_auth options through appliance_console

    Polarion:
        assignee: jdupuy
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
@pytest.mark.tier(3)
def test_ldaps_customized_port():
    """
    Configure ldap/ldaps domain server with customized port.
    Configure cfme for customized domain ports. Check mojo page for
    details.
    Verify ldap user/group authentication.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/2h
        title: Configure  ldaps for customized port e.g 10636, 10389 and validate CFME auth
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_saml_multiple_appliances_same_realm():
    """
    Verify configuring more than one appliance to SAML authentication as
    mentioned in Step#1 works fine.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/2h
        title: saml: Verify multiple appliances can be added to the same REALM.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_login_page_redirects_to_saml():
    """
    click on login to corporate account if local login is enabled,
    redirects to SAML REALM page for which user is appliance is configured
    to.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        initialEstimate: 1/4h
        title: Verify CFME login page redirects to SAML login page upon
               successful configuration
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_session_timeout():
    """
    As admin change the session timeout in cfme webui.
    Login as ldap user and verify session times out after the specified
    timeout value.

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/6h
        title: Verify session timeout works fine for external auth.
    """
    pass
