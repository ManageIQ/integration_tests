from utils.version import get_stream
from collections import namedtuple
from cfme.test_framework.sprout.client import SproutClient
from utils.conf import cfme_data, credentials
from utils.log import logger
import pytest
from wait_for import wait_for
from cfme.test_framework.sprout.client import SproutException
from fixtures.appliance import temp_appliances

TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])


@pytest.yield_fixture(scope="function")
def dedicated_db_appliance(app_creds, appliance):
    """'ap' launch appliance_console, '' clear info screen, '5/8' setup db, '1' Creates v2_key,
    '1' selects internal db, 'y' continue, '1' use partition, 'y' create dedicated db, 'pwd'
    db password, 'pwd' confirm db password + wait 360 secs and '' finish."""
    if appliance.version > '5.7':
        with temp_appliances(count=1, preconfigured=False) as apps:
            pwd = app_creds['password']
            if apps[0].version >= "5.8":
                command_set = (
                    'ap', '', '5', '1', '1', 'y', '1', 'y', pwd, TimedCommand(pwd, 360), '')
            else:
                command_set = (
                    'ap', '', '8', '1', '1', 'y', '1', 'y', pwd, TimedCommand(pwd, 360), '')
            apps[0].appliance_console.run_commands(command_set)
            wait_for(apps[0].is_dedicated_db_active)
            yield apps[0]
    else:
        raise Exception("Can't setup dedicated db on appliance below 5.7 builds")


""" The Following fixture 'fqdn_appliance' provisions one appliance for testing from an FQDN
    provider unless there are no provisions available"""


@pytest.yield_fixture(scope="function")
def fqdn_appliance(appliance):
    sp = SproutClient.from_config()
    available_providers = set(sp.call_method('available_providers'))
    required_providers = set(cfme_data['fqdn_providers'])
    usable_providers = available_providers & required_providers
    version = appliance.version.vstring
    stream = get_stream(appliance.version)
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

    apps[0].ssh_client.close()
    sp.destroy_pool(pool_id)


@pytest.yield_fixture()
def ipa_crud(fqdn_appliance, app_creds, ipa_creds):
    fqdn_appliance.appliance_console_cli.configure_ipa(ipa_creds['ipaserver'],
        ipa_creds['username'], ipa_creds['password'], ipa_creds['domain'], ipa_creds['realm'])

    yield(fqdn_appliance)


@pytest.fixture()
def app_creds():
    return {
        'username': credentials['database']['username'],
        'password': credentials['database']['password'],
        'sshlogin': credentials['ssh']['username'],
        'sshpass': credentials['ssh']['password']
    }


@pytest.fixture(scope="module")
def app_creds_modscope():
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
