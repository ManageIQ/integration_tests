from urllib.parse import urlparse

import attr
import pytest

from cfme.fixtures.pytest_store import store
from cfme.utils.appliance import DummyAppliance
from cfme.utils.appliance import load_appliances_from_config
from cfme.utils.appliance import stack
from cfme.utils.path import log_path
from .regular import APP_TYPE as DEFAULT_APP_TYPE

PLUGIN_KEY = "appliance-holder"


def pytest_addoption(parser):
    group = parser.getgroup("appliances")
    # common appliance options
    group.addoption('--app-version', default=None, dest='app-version')
    group.addoption('--use-apps', default=[DEFAULT_APP_TYPE], dest='app-types', nargs='+')


def appliances_from_cli(cli_appliances, appliance_version):
    appliance_config = dict(appliances=[])
    for appliance_data in cli_appliances:
        parsed_url = urlparse(appliance_data['hostname'])
        if not parsed_url.hostname:
            raise ValueError(
                "Invalid appliance url: {}".format(appliance_data)
            )

        appliance = appliance_data.copy()
        appliance.update(dict(
            hostname=parsed_url.hostname,
            ui_protocol=parsed_url.scheme if parsed_url.scheme else "https",
            ui_port=parsed_url.port if parsed_url.port else 443,
            version=appliance_version
        ))

        appliance_config['appliances'].append(appliance)

    return load_appliances_from_config(appliance_config)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    # TODO: get rid of below
    plugin = ApplianceHolderPlugin(None, {})
    config.pluginmanager.register(plugin, PLUGIN_KEY)

    if config.getoption('--help'):
        return


def pytest_sessionstart(session):
    holder = session.config.pluginmanager.getplugin('appliance-holder')
    if isinstance(holder.held_appliance, DummyAppliance) or holder.held_appliance.is_dev:
        return
    if store.parallelizer_role != 'slave':
        with log_path.join('appliance_version').open('w') as appliance_version:
            appliance_version.write(holder.held_appliance.version.vstring)


@attr.s(cmp=False)
class ApplianceHolderPlugin(object):
    held_appliance = attr.ib()
    pools = attr.ib(type=dict)
    stack = attr.ib(default=stack)
