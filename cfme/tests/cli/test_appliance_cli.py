from fixtures.pytest_store import store
from utils.log_validator import LogValidator
import pytest


def test_set_hostname(request):
    store.current_appliance.ap_cli.set_hostname('test.example.com')
    return_code, output = store.current_appliance.ssh_client.run_command(
        "hostname -f")
    assert output.strip() == 'test.example.com'
    assert return_code == 0


def test_configure_appliance_internal_fetch_key(request, app_creds, appliance):
    fetch_key_ip = store.current_appliance.address
    appliance.ap_cli.configure_appliance_internal_fetch_key(0, 'localhost',
        app_creds['username'], app_creds['password'], 'vmdb_production', fetch_key_ip,
        app_creds['sshlogin'], app_creds['sshpass'])
    appliance.wait_for_evm_service()
    appliance.wait_for_web_ui()


def test_configure_appliance_external_join(request, app_creds, appliance):
    appliance_ip = store.current_appliance.address
    appliance.ap_cli.configure_appliance_external_join(appliance_ip,
        app_creds['username'], app_creds['password'], 'vmdb_production', appliance_ip,
        app_creds['sshlogin'], app_creds['sshpass'])
    appliance.wait_for_evm_service()
    appliance.wait_for_web_ui()


def test_configure_appliance_external_create(request, app_creds, appliance, dedicated_db):
    HOST = dedicated_db.address
    appliance.ap_cli.configure_appliance_external_create(5, HOST,
        app_creds['username'], app_creds['password'], 'vmdb_production', HOST,
        app_creds['sshlogin'], app_creds['sshpass'])
    appliance.wait_for_evm_service()
    appliance.wait_for_web_ui()
    return_code, output = appliance.ssh_client.run_command("cat /var/www/miq/vmdb/REGION | grep 5")
    assert return_code == 0


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


def test_ipa_crud(request, ipa_creds, fqdn_appliance):
    fqdn_appliance.ap_cli.configure_ipa(ipa_creds['ipaserver'], ipa_creds['username'],
        ipa_creds['password'], ipa_creds['domain'], ipa_creds['realm'])
    fqdn_appliance.ap_cli.uninstall_ipa_client()
