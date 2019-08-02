import pytest
from wait_for import wait_for

from cfme import test_requirements
from cfme.utils.log_validator import LogValidator

pytestmark = [
    test_requirements.app_console,
    pytest.mark.uncollectif(lambda appliance: appliance.is_pod,
                            reason="cli isn't supported in pod appliance")
]

tzs = [
    ['Africa/Abidjan'],
    ['America/Argentina/Buenos_Aires'],
    ['Antarctica/Casey'],
    ['Arctic/Longyearbyen'],
    ['Asia/Aden'],
    ['Atlantic/Azores'],
    ['Australia/Adelaide'],
    ['Europe/Amsterdam'],
    ['Indian/Antananarivo'],
    ['Pacific/Apia'],
    ['UTC'],
]


@pytest.mark.tier(1)
def test_appliance_console_cli_datetime(temp_appliance_preconfig_funcscope):
    """Grab fresh appliance and set time and date through appliance_console_cli and check result

    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/6h
    """
    app = temp_appliance_preconfig_funcscope
    app.ssh_client.run_command("appliance_console_cli --datetime 2020-10-20T09:59:00")

    def date_changed():
        return app.ssh_client.run_command("date +%F-%T | grep 2020-10-20-10:00").success
    wait_for(date_changed)


@pytest.mark.rhel_testing
@pytest.mark.parametrize('timezone', tzs, ids=[tz[0] for tz in tzs])
@pytest.mark.tier(2)
def test_appliance_console_cli_timezone(timezone, temp_appliance_preconfig_modscope):
    """Set and check timezones are set correctly through appliance conosle cli

    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/12h
    """
    app = temp_appliance_preconfig_modscope
    app.ssh_client.run_command("appliance_console_cli --timezone {}".format(timezone))
    app.appliance_console.timezone_check(timezone)


@pytest.mark.tier(2)
def test_appliance_console_cli_set_hostname(configured_appliance):
    """
    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/12h
    """
    hostname = 'test.example.com'
    configured_appliance.appliance_console_cli.set_hostname(hostname)
    result = configured_appliance.ssh_client.run_command("hostname -f")
    assert result.success
    assert result.output.strip() == hostname


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
def test_appliance_console_cli_internal_fetch_key(app_creds, unconfigured_appliance, appliance):
    """
    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/3h
    """
    fetch_key_ip = appliance.hostname
    unconfigured_appliance.appliance_console_cli.configure_appliance_internal_fetch_key(
        0, 'localhost', app_creds['username'], app_creds['password'], 'vmdb_production',
        unconfigured_appliance.unpartitioned_disks[0], fetch_key_ip, app_creds['sshlogin'],
        app_creds['sshpass'])
    unconfigured_appliance.evmserverd.wait_for_running()
    unconfigured_appliance.wait_for_web_ui()


@pytest.mark.tier(2)
def test_appliance_console_cli_external_join(app_creds, appliance,
                                             temp_appliance_unconfig_funcscope):
    """
    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    appliance_ip = appliance.hostname
    temp_appliance_unconfig_funcscope.appliance_console_cli.configure_appliance_external_join(
        appliance_ip, app_creds['username'], app_creds['password'], 'vmdb_production', appliance_ip,
        app_creds['sshlogin'], app_creds['sshpass'])
    temp_appliance_unconfig_funcscope.evmserverd.wait_for_running()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
def test_appliance_console_cli_external_create(app_creds, dedicated_db_appliance,
                                               unconfigured_appliance_secondary):
    """
    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/3h
    """
    hostname = dedicated_db_appliance.hostname
    unconfigured_appliance_secondary.appliance_console_cli.configure_appliance_external_create(5,
        hostname, app_creds['username'], app_creds['password'], 'vmdb_production', hostname,
        app_creds['sshlogin'], app_creds['sshpass'])
    unconfigured_appliance_secondary.evmserverd.wait_for_running()
    unconfigured_appliance_secondary.wait_for_web_ui()


@pytest.mark.parametrize('auth_type', ['sso_enabled', 'saml_enabled', 'local_login_disabled'],
    ids=['sso', 'saml', 'local_login'])
def test_appliance_console_cli_external_auth(auth_type, ipa_crud, configured_appliance):
    """
    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Auth
        initialEstimate: 1/4h
    """
    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to true.*'.format(auth_type)],
                            hostname=configured_appliance.hostname)
    evm_tail.start_monitoring()
    cmd_set = 'appliance_console_cli --extauth-opts="/authentication/{}=true"'.format(auth_type)
    assert configured_appliance.ssh_client.run_command(cmd_set)
    assert evm_tail.validate(wait="30s")

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to false.*'.format(auth_type)],
                            hostname=configured_appliance.hostname)

    evm_tail.start_monitoring()
    cmd_unset = 'appliance_console_cli --extauth-opts="/authentication/{}=false"'.format(auth_type)
    assert configured_appliance.ssh_client.run_command(cmd_unset)
    assert evm_tail.validate(wait="30s")


@pytest.fixture(scope='function')
def no_ipa_config(configured_appliance):
    """Make sure appliance doesn't have IPA configured"""
    configured_appliance.appliance_console_cli.uninstall_ipa_client()


@pytest.mark.rhel_testing
def test_appliance_console_cli_ipa(ipa_crud, configured_appliance, no_ipa_config):
    """
    Polarion:
        assignee: mnadeem
        caseimportance: high
        initialEstimate: 1/4h
        casecomponent: Auth
    """
    ipa_args = ipa_crud.as_external_value()
    configured_appliance.appliance_console_cli.configure_ipa(**ipa_args)
    assert wait_for(lambda: configured_appliance.sssd.running)
    configured_appliance.appliance_console_cli.uninstall_ipa_client()
    assert wait_for(lambda: not configured_appliance.sssd.running)


@pytest.mark.tier(1)
def test_appliance_console_cli_extend_storage(unconfigured_appliance):
    """
    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/6h
    """
    unconfigured_appliance.ssh_client.run_command('appliance_console_cli -t /dev/vdb')

    def is_storage_extended():
        assert unconfigured_appliance.ssh_client.run_command("df -h | grep /var/www/miq_tmp")
    wait_for(is_storage_extended)


@pytest.mark.tier(1)
def test_appliance_console_cli_extend_log_storage(unconfigured_appliance):
    """
    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/6h
    """
    unconfigured_appliance.ssh_client.run_command('appliance_console_cli -l /dev/vdb')

    def is_storage_extended():
        assert unconfigured_appliance.ssh_client.run_command("df -h | grep /vg_miq_logs")
    wait_for(is_storage_extended)


@pytest.mark.rhel_testing
@pytest.mark.tier(1)
def test_appliance_console_cli_configure_dedicated_db(unconfigured_appliance, app_creds):
    """
    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/6h
    """
    unconfigured_appliance.appliance_console_cli.configure_appliance_dedicated_db(
        app_creds['username'], app_creds['password'], 'vmdb_production',
        unconfigured_appliance.unpartitioned_disks[0]
    )
    wait_for(lambda: unconfigured_appliance.db.is_dedicated_active)


@pytest.mark.tier(2)
def test_appliance_console_cli_ha_crud(unconfigured_appliances, app_creds):
    """Tests the configuration of HA with three appliances including failover to standby node

    Polarion:
        assignee: sbulage
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1h
    """
    apps = unconfigured_appliances
    app0_ip = apps[0].hostname
    app1_ip = apps[1].hostname
    # Configure primary database
    apps[0].appliance_console_cli.configure_appliance_dedicated_db(
        app_creds['username'], app_creds['password'], 'vmdb_production',
        apps[0].unpartitioned_disks[0]
    )
    wait_for(lambda: apps[0].db.is_dedicated_active)
    # Configure webui access on EVM appliance
    apps[2].appliance_console_cli.configure_appliance_external_create(1,
        app0_ip, app_creds['username'], app_creds['password'], 'vmdb_production', app0_ip,
        app_creds['sshlogin'], app_creds['sshpass'])
    apps[2].evmserverd.wait_for_running()
    apps[2].wait_for_web_ui()
    # Configure primary node
    apps[0].appliance_console_cli.configure_appliance_dedicated_ha_primary(
        app_creds['username'], app_creds['password'], 'primary', app0_ip, '1', 'vmdb_production'
    )
    # Configure standby node
    apps[1].appliance_console_cli.configure_appliance_dedicated_ha_standby(
        app_creds['username'], app_creds['password'], 'standby', app0_ip, app1_ip, '2',
        'vmdb_production', apps[1].unpartitioned_disks[0]
    )
    # Configure automatic failover on EVM appliance
    command_set = ('ap', '', '8', '1', '')
    apps[2].appliance_console.run_commands(command_set)

    wait_for(is_ha_monitor_started, func_args=[apps[2], app1_ip], timeout=300, handle_exception=True)
    # Cause failover to occur
    result = apps[0].ssh_client.run_command('systemctl stop $APPLIANCE_PG_SERVICE', timeout=15)
    assert result.success, "Failed to stop APPLIANCE_PG_SERVICE: {}".format(result.output)

    def is_failover_started(appliance):
        return appliance.ssh_client.run_command(
            "grep 'Starting to execute failover' /var/www/miq/vmdb/log/ha_admin.log").success
    wait_for(is_failover_started, func_args=[apps[2]], timeout=450, handle_exception=True)
    apps[2].evmserverd.wait_for_running()
    apps[2].wait_for_web_ui()
