from cfme.utils.version import get_stream
from collections import namedtuple
from contextlib import contextmanager
from cfme.test_framework.sprout.client import SproutClient
from cfme.utils.conf import cfme_data, credentials, auth_data
from cfme.utils.log import logger
import pytest
from wait_for import wait_for
from cfme.test_framework.sprout.client import SproutException
from fixtures.appliance import temp_appliances

TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])

""" The Following fixtures are for provisioning one preconfigured or unconfigured appliance for
    testing from an FQDN provider unless there are no provisions available"""


@contextmanager
def fqdn_appliance(appliance, preconfigured, count):
    sp = SproutClient.from_config()
    available_providers = set(sp.call_method('available_providers'))
    required_providers = set(cfme_data['fqdn_providers'])
    usable_providers = available_providers & required_providers
    version = appliance.version.vstring
    stream = get_stream(appliance.version)
    for provider in usable_providers:
        try:
            apps, pool_id = sp.provision_appliances(
                count=count, preconfigured=preconfigured, version=version, stream=stream,
                provider=provider
            )
            break
        except Exception as e:
            logger.warning("Couldn't provision appliance with following error:")
            logger.warning("{}".format(e))
            continue
    else:
        logger.error("Couldn't provision an appliance at all")
        raise SproutException('No provision available')
    yield apps
    for app in apps:
        app.ssh_client.close()
    sp.destroy_pool(pool_id)


@pytest.yield_fixture()
def unconfigured_appliance(appliance):
    with fqdn_appliance(appliance, preconfigured=False, count=1) as apps:
        yield apps[0]


@pytest.yield_fixture()
def unconfigured_appliance_secondary(appliance):
    with fqdn_appliance(appliance, preconfigured=False, count=1) as apps:
        yield apps[0]


@pytest.yield_fixture()
def unconfigured_appliances(appliance):
    with fqdn_appliance(appliance, preconfigured=False, count=3) as apps:
        yield apps


@pytest.yield_fixture()
def configured_appliance(appliance):
    with fqdn_appliance(appliance, preconfigured=True, count=1) as apps:
        yield apps[0]


@pytest.yield_fixture(scope="function")
def dedicated_db_appliance(app_creds, unconfigured_appliance):
    """'ap' launch appliance_console, '' clear info screen, '5' setup db, '1' Creates v2_key,
    '1' selects internal db, '1' use partition, 'y' create dedicated db, 'pwd'
    db password, 'pwd' confirm db password + wait 360 secs and '' finish."""
    app = unconfigured_appliance
    pwd = app_creds['password']
    command_set = ('ap', '', '5', '1', '1', '1', 'y', pwd, TimedCommand(pwd, 360), '')
    app.appliance_console.run_commands(command_set)
    wait_for(lambda: app.db.is_dedicated_active)
    yield app


@pytest.fixture(scope="function")
def appliance_with_preset_time(temp_appliance_preconfig_funcscope):
    """Grabs fresh appliance and sets time and date prior to running tests"""
    temp_appliance_preconfig_funcscope.ssh_client.run_command(
        "appliance_console_cli --datetime 2020-10-20T09:58:00")
    return temp_appliance_preconfig_funcscope


@pytest.yield_fixture()
def ipa_crud(configured_appliance, ipa_creds):
    configured_appliance.appliance_console_cli.configure_ipa(ipa_creds['ipaserver'],
        ipa_creds['username'], ipa_creds['password'], ipa_creds['domain'], ipa_creds['realm'])

    yield(configured_appliance)


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
    try:
        ext_ipa = auth_data['auth_providers']['ext_ipa']
    except KeyError:
        pytest.skip('Missing auth_providers.ext_ipa in auth_data.yaml')
    fqdn = ext_ipa['ipaserver'].split('.', 1)
    creds_key = ext_ipa['credentials']
    return{
        'hostname': fqdn[0],
        'domain': fqdn[1],
        'realm': ext_ipa['iparealm'],
        'ipaserver': ext_ipa['ipaserver'],
        'username': credentials[creds_key]['principal'],
        'password': credentials[creds_key]['password']
    }
