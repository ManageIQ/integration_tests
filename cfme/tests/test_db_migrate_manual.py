import pytest

from cfme import test_requirements

@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
@pytest.mark.ignore_stream('5.9', '5.10')
def test_upgrade_single_inplace_postgres():
    """
    Upgrading a single appliance and upgrade postgres to 9.5

    Polarion:
        assignee: jhenner
        casecomponent: appl
        caseimportance: critical
        endsin: 5.8
        initialEstimate: 1/2h
        setup: Run inplace upgrade and postgres upgrade
               Migration docs at (https://mojo.redhat.com/docs/DOC-1058772)
               Check new postgress is running correctly
        startsin: 5.7
        testtype: upgrade
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_upgrade_dedicated_db_migration_local():
    """
    Test that you can locally migrate a dedicated database after upgrade.
    Previously it was missing the database.yml during setup with would
    case the rake task to fail.
    https://bugzilla.redhat.com/show_bug.cgi?id=1478986

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.8
        testSteps:
            1. Upgrade appliances
            2. Check failover
        expectedResults:
            1. Confirm upgrade completes successfully
            2. Confirm failover continues to work
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_upgrade_single_inplace_ipv6():
    """
    Upgrading a single appliance on ipv6 only env

    Polarion:
        assignee: jhenner
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: provision appliance
               add provider
               add repo file to /etc/yum.repos.d/
               run "yum update"
               run "rake db:migrate"
               run "rake evm:automate:reset"
               run "systemctl start evmserverd"
               check webui is available
               add additional provider/provision vms
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_upgrade_single_negative_v2_key_fix_auth():
    """
    test migration without fetching v2_key also requires fix_auth

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/3h
        setup: restore a backup without using its v2_key
               run "fix_auth --invalid <password>"
               this will allow evm to start without credential errors
        testtype: upgrade
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_upgrade_custom_css():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1553841
    Test css customization"s function correctly after upgrades.

    Polarion:
        assignee: jhenner
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/6h
        setup: provision appliance
               add custom css file
               add repo file to /etc/yum.repos.d/
               run "yum update"
               run "rake db:migrate"
               run "rake evm:automate:reset"
               run "systemctl start evmserverd"
               check webui is available
               check customization"s still work
        startsin: 5.10
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_upgrade_custom_widgets():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1375313
    Upgrade appliance with custom widgets added

    Polarion:
        assignee: jhenner
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: provision appliance
               add custom widgets
               add repo file to /etc/yum.repos.d/
               run "yum update"
               run "rake db:migrate"
               run "rake evm:automate:reset"
               run "systemctl start evmserverd"
               check webui is available
               check widgets still work correctly
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_rh_rhsm_sat6_cred_save_crud():
    """
    Switch between rhsm and sat6 setup
    https://bugzilla.redhat.com/show_bug.cgi?id=1463389

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
        setup: Provision appliance
               navigate to Configuration-settings-region-redhat updates
               Click edit subscription
               Setup rhsm subscription
               Save (validate and save if fails)
               edit subscription
               setup sat6
               click save
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
@pytest.mark.ignore_stream('5.10')
def test_upgrade_rubyrep_to_pglogical():
    """
    Test upgrading appliances in ruby replication and change it over to
    pglogical

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        endsin: 5.9
        initialEstimate: 1h
        setup: provision 2 appliances
               setup rubyrep between them
               test replication is working
               stop replication
               upgrade appliances following version dependent docs found here
               https://mojo.redhat.com/docs/DOC-1058772
               configure pglogical replication
               confirm replication is working correctly
        startsin: 5.6
        testtype: upgrade
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_upgrade_multi_ext_inplace():
    """
    test_upgrade_multi_ext_inplace

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1h
        setup: 2 appliances:
               - Appliance A: internal DB, region 0
               - Appliance B: external DB, pointed at A, region 0
               - Setup LDAP on one of the appliances
               - Login as LDAP user A
               - Setup a provider
               - Provision a VM
        testtype: upgrade
        testSteps:
            1. Run upgrade according to the migration guide (version-dependent)
            2. Start the appliances back up
            3. Login as LDAP user B
            4. Add another provider
            5. Provision another VM using the new provider
            6. Visit provider/host/vm summary pages
        expectedResults:
            1. Upgrade is successful, so is migration and related tasks (fix_auth)
            2. Appliances are running
            3. Login is successful
            4. Provider added
            5. VM provisioned
            6. Summary pages can be loaded and show correct information
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_update_custom_widgets():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1375313
    Upgrade appliance with custom widgets added

    Polarion:
        assignee: jhenner
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: provision appliance
               add custom widgets
               add repo file to /etc/yum.repos.d/
               add RHSM details
               check for updates
               update using webui
               check webui is available
               check widgets still work correctly
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_rh_registration_rhsm_proxy_on_ipv6():
    """
    Test RHSM registration with IPV6 proxy settings

    Polarion:
        assignee: jhenner
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/12h
        setup: Provision appliace
               Connect to webui
               Nav to Configuration-Settings-Region-Red Hat Updates
               Edit Registration
               The following settings that work for internal testing
               can be found here https://mojo.redhat.com/docs/DOC-1123648
               Save settings
               Select appliance and click register
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_rh_registration_ui_proxy():
    """
    Check proxy settings are show in the list of info after saving
    subscription using proxy settings (RFE)

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/12h
        setup: Provision appliance
               navigate to Configuration-settings-region-redhat updates
               Click edit subscription
               Setup subscription with proxy
               validate and save
               check proxy settings areshown in ui
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_update_webui_custom_css():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1553841
    Test css customization"s function correctly after webui update.

    Polarion:
        assignee: jhenner
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/6h
        setup: provision appliance
               add custom css file
               add repo file to /etc/yum.repos.d/
               add RHSM settings
               update through webui
               check webui is available
               check customization"s still work
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_rh_registration_proxy_crud():
    """
    Check proxy settings get added and removed from /etc/rhsm/rhsm.conf
    https://bugzilla.redhat.com/show_bug.cgi?id=1463289

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/12h
        setup: Provision appliance
               navigate to Configuration-settings-region-redhat updates
               Click edit subscription
               Setup subscription with proxy
               validate and save
               check proxy settings are added to rhsm.conf
               edit subscription again
               remove proxy settings
               validate and save
               check proxy settings are removed from rhsm.conf
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_rh_unregistration_ui():
    """
    Check that you can unregister an appliance from subscriptions through
    the ui.
    https://bugzilla.redhat.com/show_bug.cgi?id=1464387

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/12h
        setup: Provision appliance
               navigate to Configuration-settings-region-redhat updates
               Click edit subscription
               Setup subscription
               validate and save
               Register appliance
               Try to unregister
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_upgrade_multi_replication_inplace():
    """
    test_upgrade_multi_replication_inplace

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1h
        setup: 2 appliances:
               - Appliance A: internal DB, region 0
               - Appliance B: external DB, pointed at A, region 0
               - Setup LDAP on one of the appliances
               - Login as LDAP user A
               - Setup a provider
               - Provision a VM
        testtype: upgrade
        testSteps:
            1. Run upgrade according to the migration guide (version-dependent)
            2. Start the appliances back up
            3. Login as LDAP user B
            4. Add another provider
            5. Provision another VM using the new provider
            6. Visit provider/host/vm summary pages
        expectedResults:
            1. Upgrade is successful, so is migration and related tasks (fix_auth)
            2. Appliances are running
            3. Login is successful
            4. Provider added
            5. VM provisioned
            6. Summary pages can be loaded and show correct information
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_update_webui_ipv6():
    """
    Test updating the appliance to release version from prior version.
    (i.e 5.5.x to 5.5.x+) IPV6 only env

    Polarion:
        assignee: jhenner
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/3h
        setup: -Provision configured appliance
               -Register it with RHSM using web UI
               -Create /etc/yum.repos.d/update.repo
               -populate file with repos from
               https://mojo.redhat.com/docs/DOC-1058772
               -check for update in web UI
               -apply update
               -appliance should shutdown update and start back up
               -confirm you can login afterwards
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_upgrade_check_repo_names():
    """
    Checks default rpm repos on a upgraded appliance
    https://bugzilla.redhat.com/show_bug.cgi?id=1411890

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/12h
        setup: Provision appliance
               navigate to Configuration-settings-region-redhat updates
               Click edit subscription
               Check repo name
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_upgrade_appliance_console_scap():
    """
    "ap" launches appliance_console, "" clears info screen, "14/17"
    Hardens appliance using SCAP configuration, "" complete.
    apply scap rules upgrade appliance and re-apply scap rules
    Test Source

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/3h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_upgrade_multi_ha_inplace():
    """
    Test upgrading HA setup to latest build and confirm it continues to
    work as expected.

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.8
        testSteps:
            1. Upgrade appliances
            2. Check failover
        expectedResults:
            1. Confirm upgrade completes successfully
            2. Confirm failover continues to work
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
@pytest.mark.ignore_stream('5.10')
def test_upgrade_multi_replication_inplace_55():
    """
    test upgrading replicated appliances to latest version

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        endsin: 5.9
        initialEstimate: 1h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
@pytest.mark.ignore_stream('5.11')
def test_upgrade_multi_replication_inplace_56():
    """
    test upgrading replicated appliances to latest version

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        endsin: 5.10
        initialEstimate: 1h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_update_webui_ha():
    """
    Test webui update from minor versions with HA active

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/2h
        setup: provision 3 appliances
               setup HA following https://mojo.redhat.com/docs/DOC-1097888
               check setup is working by accessing webui
               add repos for new build
               login to RHSM
               check for updates
               update appliances
               confirm HA continues to work as expected after update
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_rh_rhsm_reregistering():
    """
    Switch between rhsm and sat6 registration
    https://bugzilla.redhat.com/show_bug.cgi?id=1461716

    Polarion:
        assignee: jhenner
        casecomponent: config
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
        setup: Provision appliance
               navigate to Configuration-settings-region-redhat updates
               Click edit subscription
               Setup sat6 subscription
               validate and save
               register
               unregister (requires ssh commands)
               edit subscription
               setup rhsm
               validate and save
               register
    """
    pass


@pytest.mark.manual
@test_requirements.upgrade
@pytest.mark.tier(2)
def test_update_webui_replication():
    """
    Test webui update with replicated env

    Polarion:
        assignee: jhenner
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1h
        setup: Provision two appliances of the previous minor build
               setup replication between the two
               add update.repo file to /etc/yum.repos.d/
               populate file with correct repos from
               https://mojo.redhat.com/docs/DOC-1058772
               register with RHSM in webui
               check for updates
               apply update
               check replication/providers/vms
        testtype: upgrade
    """
    pass
