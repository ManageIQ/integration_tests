from utils.version import get_stream
from cfme.test_framework.sprout.client import SproutClient
from utils.appliance import current_appliance
from utils.conf import cfme_data, credentials
from utils.log import logger
import pytest
import paramiko


@pytest.fixture()
def dedicated_db(appliance, app_creds):
    HOST = appliance.address
    USER = app_creds['username']
    PASS = app_creds['password']
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS)
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdin.write("ap \n 8 \n 1 \n 1 \n 1 \n y \n {PASS} \n {PASS} \n \n")

    return appliance


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


@pytest.yield_fixture()
def ipa_crud(fqdn_appliance, app_creds, ipa_creds):
    fqdn_appliance.ap_cli.configure_ipa(ipa_creds['ipaserver'], ipa_creds['username'],
        ipa_creds['password'], ipa_creds['domain'], ipa_creds['realm'])

    yield(fqdn_appliance)

    fqdn_appliance.ap_cli.uninstall_ipa_client()


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
