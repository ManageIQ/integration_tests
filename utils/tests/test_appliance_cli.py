from fixtures.pytest_store import store
from utils import version
from utils.appliance import provision_appliance
import pytest


def test_set_hostname(request):
    store.current_appliance.ap_cli.set_hostname('test.example.com')
    return_code, output = store.current_appliance.ssh_client.run_command(
        "cat /etc/hosts | grep test.example.com")
    assert return_code == 0


@pytest.yield_fixture
def provisioned_appliance():
    ver_to_prov = str(version.current_version())
    app = provision_appliance(version=ver_to_prov)

    yield app

    app.destroy()

# Work in progress trying to simplify strings


def test_configure_appliance_internal_fetch_key(request, provisioned_appliance):
    app = provisioned_appliance
    app.ap_cli.configure_appliance_fetch_key(db_configuration)
    db_configuration = ('-r 0 -i -h localhost -U {} -p {} -d {} -k {} -v -K {} -s {} -a {}')
    assert app.is_evm_service_running()
    assert app.is_web_ui_running()


def test_configure_ipa(request):
    current_appliance.ap_cli.configure_ipa(
        hostname, domain, realm, username, password)
    return_code, output = (current_appliance.ssh.run_command(
        "systemctl status sssd | grep running"))
    assert return_code == 0
    return_code, output = (current_appliance.ssh.run_command(
        "cat /etc/ipa/default.conf | grep enable_ra = True"))
    assert return_code == 0


def test_uninstall_ipa(request):
    current_appliance.ap_cli.uninstall_ipa()
    return_code, output = (current_appliance.ssh.run_command("cat /etc/ipa/default.conf"))
    assert return_code == 0
