from utils.version import get_stream
from cfme.test_framework.sprout.client import SproutClient
from utils.appliance import current_appliance
from utils.conf import cfme_data, credentials
from utils.db import scl_name
from utils.log import logger
import pytest
from wait_for import wait_for
from cfme.test_framework.sprout.client import SproutException


@pytest.fixture()
def dedicated_db(fqdn_appliance, app_creds):
    def is_dedicated_db_active(dedicated_db):
        return_code, output = dedicated_db.ssh_client.run_command(
            "systemctl status rh-postgresql{}-postgresql.service | grep running".format(scl_name()))
        return return_code == 0
    pwd = app_creds['password']
    client = fqdn_appliance.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdin.write("ap \n \n 8 \n 1 \n 1 \n 1 \n y \n {} \n {} \n \n".format(pwd, pwd))
    wait_for(is_dedicated_db_active, func_args=[fqdn_appliance])

    return (fqdn_appliance)


@pytest.yield_fixture(scope="function")
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
            logger.warning("{}".format(e))
            continue
    else:
        logger.error("Couldn't provision an appliance at all")
        raise SproutException('No provision available')
    yield apps[0]

    sp.destroy_pool(pool_id)


@pytest.yield_fixture(scope="module")
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
