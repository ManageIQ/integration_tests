from fixtures.pytest_store import store
from utils.version import get_stream
from cfme.test_framework.sprout.client import SproutClient
from utils.appliance import current_appliance
from utils.conf import cfme_data, credentials
from utils.log import logger
import pytest


@pytest.yield_fixture(scope="module")
def appliance():
    sp = SproutClient.from_config()
    version = current_appliance.version.vstring
    stream = get_stream(current_appliance.version)
    apps, pool_id = sp.provision_appliances(
        count=1, preconfigured=False, version=version, stream=stream)

    yield apps[0]

    sp.destroy_pool(pool_id)


@pytest.yield_fixture(scope="module")
def fqdn_appliance():
    sp = SproutClient.from_config()
    available_providers = set(sp.call_method('available_providers'))
    required_providers = set(cfme_data['fqdn_providers'])
    usable_providers = available_providers & required_providers
    version = current_appliance.version.vstring
    stream = get_stream(current_appliance.version)

    for provider in usable_providers:
        try:
            apps, pool_id = sp.provision_appliances(
                count=1, preconfigured=True, version=version, stream=stream, provider=provider)
            break
        except Exception as e:
            logger.warning("Couldn't provision appliance with following error:")
            logger.warning({}.format(e))
            continue
    else:
        logger.error("Couldn't provision an appliance at all")

    yield apps[0]

    sp.destroy_pool(pool_id)


@pytest.fixture()
def app_creds():
    return {
        'username': credentials['database']['username'],
        'password': credentials['database']['password'],
        'sshlogin': credentials['ssh']['username'],
        'sshpass': credentials['ssh']['password']
    }


@pytest.fixture()
def ipa_creds():
    fqdn = cfme_data['auth_modes']['ext_ipa']['ipaserver'].split('.', 1)
    creds_key = cfme_data['auth_modes']['ext_ipa']['credentials']
    return{
        'hostname': fqdn[0],
        'domain': fqdn[1],
        'realm': cfme_data['auth_modes']['ext_ipa']['iparealm'],
        'ipaserver': cfme_data['auth_modes']['ext_ipa']['ipaserver'],
        'username': credentials[creds_key]['principal'],
        'password': credentials[creds_key]['password']
    }


def test_set_hostname(request):
    store.current_appliance.ap_cli.set_hostname('test.example.com')
    return_code, output = store.current_appliance.ssh_client.run_command(
        "hostname -f")
    assert output.strip() == 'test.example.com'
    assert return_code == 0


def test_configure_appliance_internal_fetch_key(request, app_creds, appliance):
    app = appliance
    fetch_key_ip = store.current_appliance.address
    app.ap_cli.configure_appliance_internal_fetch_key(0, 'localhost',
        app_creds['username'], app_creds['password'], 'vmdb_production', fetch_key_ip,
        app_creds['sshlogin'], app_creds['sshpass'])
    app.wait_for_evm_service()
    app.wait_for_web_ui()


def test_ipa_crud(request, ipa_creds, fqdn_appliance):
    app = fqdn_appliance
    app.ap_cli.configure_ipa(ipa_creds['ipaserver'], ipa_creds['username'],
        ipa_creds['password'], ipa_creds['domain'], ipa_creds['realm'])
    assert app.ssh_client.run_command("systemctl status sssd | grep running")
    return_code, output = app.ssh_client.run_command(
        "cat /etc/ipa/default.conf | grep 'enable_ra = True'")
    assert return_code == 0   # TODO extend test to login as ipa user
    app.ap_cli.uninstall_ipa_client()
    return_code, output = app.ssh_client.run_command(
        "cat /etc/ipa/default.conf")
    assert return_code != 0
