from fixtures.pytest_store import store
from utils import version
from utils.appliance import provision_appliance
from utils.conf import cfme_data, credentials
import pytest


def test_set_hostname(request):
    store.current_appliance.ap_cli.set_hostname('test.example.com')
    return_code, output = store.current_appliance.ssh_client.run_command(
        "cat /etc/hosts | grep test.example.com")
    assert return_code == 0


@pytest.yield_fixture(scope="module")
def provisioned_appliance():
    ver_to_prov = str(version.current_version())
    app = provision_appliance(version=ver_to_prov)

    yield app

    app.destroy()


@pytest.fixture()
def app_creds():
    return {
        'username': credentials['database']['username'],
        'password': credentials['database']['password'],
        'sshlogin': credentials['ssh']['username'],
        'sshpass': credentials['ssh']['password']
    }


def test_configure_appliance_internal_fetch_key(request, provisioned_appliance, app_creds):
        app = provisioned_appliance
        fetch_key_ip = store.current_appliance.address
        app.ap_cli.configure_appliance(0, 'localhost', app_creds['username'], app_creds['password'],
            'vmdb_production', fetch_key_ip, app_creds['sshlogin'], app_creds['sshpass'])
        assert app.is_evm_service_running()
        app.ipapp.wait_for_web_ui()
        assert app.is_web_ui_running()


@pytest.fixture()
def ipa_creds():
    fqdn = cfme_data['ipa']['ipaserver']
    fqdn.split('.', 1)
    return{
        'hostname': fqdn[0]
        'domain': fqdn[1]
        'realm': cfme_data['ipa']['realm']
        'username': credentials['ipa_server']['username']
        'password': credentials['ipa_server']['password']
    }


def test_configure_ipa(request, ipa_creds):
    store.current_appliance.ap_cli.configure_ipa(hostname, domain, realm, username, password)
    return_code, output = (store.current_appliance.ssh_client.run_command(
        "systemctl status sssd | grep running"))
    assert return_code == 0
    return_code, output = (store.current_appliance.ssh.run_command(
        "cat /etc/ipa/default.conf | grep enable_ra = True"))
    assert return_code == 0


def test_uninstall_ipa(request):
    store.current_appliance.ap_cli.uninstall_ipa()
    return_code, output = (store.current_appliance.ssh.run_command("cat /etc/ipa/default.conf"))
    assert return_code == 0
