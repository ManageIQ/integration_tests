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

    # app.destroy()


@pytest.fixture()
def app_creds():
    return {
        'username': credentials['database']['username'],
        'password': credentials['database']['password'],
        'sshlogin': credentials['ssh']['username'],
        'sshpass': credentials['ssh']['password']
    }


def test_configure_appliance_internal_fetch_key(request, app_creds, provisioned_appliance):
    app = provisioned_appliance
    fetch_key_ip = store.current_appliance.address
    app.ipapp.ap_cli.configure_appliance_internal_fetch_key(0, 'localhost',
        app_creds['username'], app_creds['password'], 'vmdb_production', fetch_key_ip,
        app_creds['sshlogin'], app_creds['sshpass'])
    app.ipapp.wait_for_evm_service()
    assert app.ipapp.is_evm_service_running()
    app.ipapp.wait_for_web_ui()
    assert app.ipapp.is_web_ui_running()


@pytest.fixture()
def ipa_creds():
    fqdn = cfme_data['ipa']['ipaserver'].split('.', 1)
    return{
        'hostname': fqdn[0],
        'domain': fqdn[1],
        'realm': cfme_data['ipa']['iparealm'],
        'ipaserver': cfme_data['ipa']['ipaserver'],
        'username': credentials['ipa_server']['principal'],
        'password': credentials['ipa_server']['password']
    }


def test_configure_ipa(request, ipa_creds):
    store.current_appliance.ap_cli.configure_ipa(ipa_creds['ipaserver'], ipa_creds['username'],
        ipa_creds['password'], ipa_creds['domain'], ipa_creds['realm'])
    assert store.current_appliance.ssh_client.run_command("systemctl status sssd | grep running")
    return_code, output = store.current_appliance.ssh_client.run_command(
        "cat /etc/ipa/default.conf | grep 'enable_ra = True'")
    assert return_code == 0
    # TODO extend test to login as user from ipa


def test_uninstall_ipa(request):
    store.current_appliance.ap_cli.uninstall_ipa_client()
    return_code, output = store.current_appliance.ssh_client.run_command(
        "cat /etc/ipa/default.conf")
    assert return_code != 0
