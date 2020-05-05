import attr
import pytest

from .default import APP_TYPE as DEFAULT_APP_TYPE
from cfme.fixtures.pytest_store import store
from cfme.utils.appliance import DummyAppliance
from cfme.utils.appliance import stack
from cfme.utils.path import log_path

PLUGIN_KEY = "appliance-holder"


def pytest_addoption(parser):
    group = parser.getgroup("appliances")
    # common appliance options
    group.addoption('--app-version', default=None, dest='app_version')
    group.addoption('--app-type', default=DEFAULT_APP_TYPE, dest='app_type')
    group.addoption('--app-num', default=1, type=int, dest='app_num')


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
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


@attr.s(eq=False)
class ApplianceHolderPlugin:
    held_appliance = attr.ib()
    pool = attr.ib(type=list)
    stack = attr.ib(default=stack)
