
import attr
import pytest

from cfme.fixtures.pytest_store import store
from cfme.utils.appliance import DummyAppliance
from cfme.utils.appliance import stack
from cfme.utils.path import log_path
from .regular import APP_TYPE as DEFAULT_APP_TYPE

PLUGIN_KEY = "appliance-holder"


def pytest_addoption(parser):
    group = parser.getgroup("appliances")
    # common appliance options
    group.addoption('--app-version', default=None, dest='app-version')
    group.addoption('--use-apps', default=[DEFAULT_APP_TYPE], dest='app-types', nargs='+')


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    # TODO: get rid of below call
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
