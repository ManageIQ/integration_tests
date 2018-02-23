import pytest

from cfme.utils.log_validator import LogValidator
from cfme.utils import version
from wait_for import wait_for


def test_appliance_console_cli_set_hostname(appliance):
    hostname = 'test.example.com'
    appliance.appliance_console_cli.set_hostname(hostname)
    return_code, output = appliance.ssh_client.run_command("hostname -f")
    assert output.strip() == hostname
    assert return_code == 0


def test_appliance_console_cli_internal_fetch_key(app_creds, unconfigured_appliance, appliance):
    fetch_key_ip = appliance.hostname
    unconfigured_appliance.appliance_console_cli.configure_appliance_internal_fetch_key(
        0, 'localhost', app_creds['username'], app_creds['password'], 'vmdb_production',
        unconfigured_appliance.unpartitioned_disks[0], fetch_key_ip, app_creds['sshlogin'],
        app_creds['sshpass'])
    unconfigured_appliance.wait_for_evm_service()
    unconfigured_appliance.wait_for_web_ui()


def test_appliance_console_cli_external_join(app_creds, appliance,
        temp_appliance_unconfig_funcscope):
    appliance_ip = appliance.hostname
    temp_appliance_unconfig_funcscope.appliance_console_cli.configure_appliance_external_join(
        appliance_ip, app_creds['username'], app_creds['password'], 'vmdb_production', appliance_ip,
        app_creds['sshlogin'], app_creds['sshpass'])
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


def test_appliance_console_cli_external_create(
        app_creds, dedicated_db_appliance, unconfigured_appliance_secondary):
    hostname = dedicated_db_appliance.hostname
    unconfigured_appliance_secondary.appliance_console_cli.configure_appliance_external_create(5,
        hostname, app_creds['username'], app_creds['password'], 'vmdb_production', hostname,
        app_creds['sshlogin'], app_creds['sshpass'])
    unconfigured_appliance_secondary.wait_for_evm_service()
    unconfigured_appliance_secondary.wait_for_web_ui()


@pytest.mark.uncollect('No IPA servers currently available')
@pytest.mark.parametrize('auth_type', ['sso_enabled', 'saml_enabled', 'local_login_disabled'],
    ids=['sso', 'saml', 'local_login'])
def test_external_auth(auth_type, ipa_crud, app_creds):
    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to true.*'.format(auth_type)],
                            hostname=ipa_crud.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()
    command = 'appliance_console_cli --extauth-opts="/authentication/{}=true"'.format(auth_type)
    ipa_crud.ssh_client.run_command(command)
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to false.*'.format(auth_type)],
                            hostname=ipa_crud.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])

    evm_tail.fix_before_start()
    command2 = 'appliance_console_cli --extauth-opts="/authentication/{}=false"'.format(auth_type)
    ipa_crud.ssh_client.run_command(command2)
    evm_tail.validate_logs()


@pytest.mark.uncollect('No IPA servers currently available')
def test_appliance_console_cli_ipa_crud(ipa_creds, configured_appliance):
    configured_appliance.appliance_console_cli.configure_ipa(ipa_creds['ipaserver'],
        ipa_creds['username'], ipa_creds['password'], ipa_creds['domain'], ipa_creds['realm'])
    configured_appliance.appliance_console_cli.uninstall_ipa_client()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.9')
def test_appliance_console_cli_extend_storage(unconfigured_appliance):
    unconfigured_appliance.ssh_client.run_command('appliance_console_cli -t auto')

    def is_storage_extended():
        assert unconfigured_appliance.ssh_client.run_command("df -h | grep /var/www/miq_tmp")
    wait_for(is_storage_extended)


@pytest.mark.uncollectif(lambda: version.current_version() < '5.9')
def test_appliance_console_cli_extend_log_storage(unconfigured_appliance):
    unconfigured_appliance.ssh_client.run_command('appliance_console_cli -l auto')

    def is_storage_extended():
        assert unconfigured_appliance.ssh_client.run_command("df -h | grep /vg_miq_logs")
    wait_for(is_storage_extended)


@pytest.mark.uncollectif(lambda: version.current_version() < '5.9')
def test_appliance_console_cli_configure_dedicated_db(unconfigured_appliance, app_creds):
    unconfigured_appliance.appliance_console_cli.configure_appliance_dedicated_db(
        app_creds['username'], app_creds['password'], 'vmdb_production',
        unconfigured_appliance.unpartitioned_disks[0]
    )
    wait_for(lambda: unconfigured_appliance.db.is_dedicated_active)


@pytest.mark.uncollectif(lambda appliance: version.current_version() < '5.9.1')
def test_appliance_console_cli_ha_crud(unconfigured_appliances, app_creds):
    """Tests the configuration of HA with three appliances including failover to standby node"""
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
    apps[2].wait_for_evm_service()
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
    command_set = ('ap', '', '9', '1', '')
    apps[2].appliance_console.run_commands(command_set)

    def is_ha_monitor_started(appliance):
        return bool(appliance.ssh_client.run_command(
            "grep {} /var/www/miq/vmdb/config/failover_databases.yml".format(app1_ip)).success)
    wait_for(is_ha_monitor_started, func_args=[apps[2]], timeout=300, handle_exception=True)
    # Cause failover to occur
    rc, out = apps[0].ssh_client.run_command('systemctl stop $APPLIANCE_PG_SERVICE', timeout=15)
    assert rc == 0, "Failed to stop APPLIANCE_PG_SERVICE: {}".format(out)

    def is_failover_started(appliance):
        return bool(appliance.ssh_client.run_command(
            "grep 'Starting to execute failover' /var/www/miq/vmdb/log/ha_admin.log").success)
    wait_for(is_failover_started, func_args=[apps[2]], timeout=450, handle_exception=True)
    apps[2].wait_for_evm_service()
    apps[2].wait_for_web_ui()
