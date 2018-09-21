import pytest

from collections import namedtuple
from six import iteritems

import cfme.utils.auth as authutil
from cfme.fixtures.appliance import sprout_appliances
from cfme.utils.conf import credentials, auth_data
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])

""" The Following fixtures are for provisioning one preconfigured or unconfigured appliance for
    testing from an FQDN provider unless there are no provisions available"""


@pytest.fixture()
def unconfigured_appliance(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            preconfigured=False,
            count=1,
            config=pytestconfig,
            provider_type='rhevm',
    ) as apps:
        yield apps[0]


@pytest.fixture()
def unconfigured_appliance_secondary(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            preconfigured=False,
            count=1,
            config=pytestconfig,
            provider_type='rhevm',
    ) as apps:
        yield apps[0]


@pytest.fixture()
def unconfigured_appliances(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            preconfigured=False,
            count=3,
            config=pytestconfig,
            provider_type='rhevm',
    ) as apps:
        yield apps


@pytest.fixture()
def configured_appliance(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            preconfigured=True,
            count=1,
            config=pytestconfig,
            provider_type='rhevm',
    ) as apps:
        yield apps[0]


@pytest.fixture(scope="function")
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
    command_set = ('ap', '', '3', 'y', '2020-10-20', '09:58:00', 'y', '')
    temp_appliance_preconfig_funcscope.appliance_console.run_commands(command_set)

    def date_changed():
        return temp_appliance_preconfig_funcscope.ssh_client.run_command(
            "date +%F-%T | grep 2020-10-20-09").success
    wait_for(date_changed)
    return temp_appliance_preconfig_funcscope


@pytest.fixture()
def ipa_crud():
    try:
        ipa_keys = [key
                    for key, yaml in iteritems(auth_data.auth_providers)
                    if yaml.type == authutil.FreeIPAAuthProvider.auth_type]
        ipa_provider = authutil.get_auth_crud(ipa_keys[0])
    except AttributeError:
        pytest.skip('Unable to parse auth_data.yaml for freeipa server')
    except IndexError:
        pytest.skip('No freeipa server available for testing')
    logger.info('Configuring first available freeipa auth provider %s', ipa_provider)

    return ipa_provider


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
