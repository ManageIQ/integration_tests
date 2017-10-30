from cfme.utils.log_validator import LogValidator
from cfme.utils import version
import pytest


def test_set_hostname(request, appliance):
    hostname = 'test.example.com'
    appliance.appliance_console_cli.set_hostname(hostname)
    return_code, output = appliance.ssh_client.run_command("hostname -f")
    assert output.strip() == hostname
    assert return_code == 0


def test_configure_appliance_internal_fetch_key(
        request, app_creds, temp_appliance_unconfig_funcscope, appliance):
    fetch_key_ip = appliance.address
    temp_appliance_unconfig_funcscope.appliance_console_cli.configure_appliance_internal_fetch_key(
        0, 'localhost', app_creds['username'], app_creds['password'], 'vmdb_production',
        temp_appliance_unconfig_funcscope.unpartitioned_disks[0], fetch_key_ip,
        app_creds['sshlogin'], app_creds['sshpass'])
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


def test_configure_appliance_external_join(request, app_creds, appliance,
        temp_appliance_unconfig_funcscope):
    appliance_ip = appliance.address
    temp_appliance_unconfig_funcscope.appliance_console_cli.configure_appliance_external_join(
        appliance_ip, app_creds['username'], app_creds['password'], 'vmdb_production', appliance_ip,
        app_creds['sshlogin'], app_creds['sshpass'])
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_configure_appliance_external_create(
        request, app_creds, dedicated_db_appliance, temp_appliance_unconfig_funcscope):
    hostname = dedicated_db_appliance.address
    temp_appliance_unconfig_funcscope.appliance_console_cli.configure_appliance_external_create(5,
        hostname, app_creds['username'], app_creds['password'], 'vmdb_production', hostname,
        app_creds['sshlogin'], app_creds['sshpass'])
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


@pytest.mark.skip('No IPA servers currently available')
@pytest.mark.parametrize('auth_type', ['sso_enabled', 'saml_enabled', 'local_login_disabled'],
    ids=['sso', 'saml', 'local_login'])
def test_external_auth(request, auth_type, ipa_crud, app_creds):
    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to true.*'.format(auth_type)],
                            hostname=ipa_crud.address,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()
    command = 'appliance_console_cli --extauth-opts="/authentication/{}=true"'.format(auth_type)
    ipa_crud.ssh_client.run_command(command)
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to false.*'.format(auth_type)],
                            hostname=ipa_crud.address,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])

    evm_tail.fix_before_start()
    command2 = 'appliance_console_cli --extauth-opts="/authentication/{}=false"'.format(auth_type)
    ipa_crud.ssh_client.run_command(command2)
    evm_tail.validate_logs()


@pytest.mark.skip('No IPA servers currently available')
def test_ipa_crud(request, ipa_creds, fqdn_appliance):
    fqdn_appliance.appliance_console_cli.configure_ipa(ipa_creds['ipaserver'],
        ipa_creds['username'], ipa_creds['password'], ipa_creds['domain'], ipa_creds['realm'])
    fqdn_appliance.appliance_console_cli.uninstall_ipa_client()
