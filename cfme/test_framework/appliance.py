import attr
import pytest

from cfme.utils import conf

from cfme.utils.path import log_path
from cfme.utils.appliance import load_appliances_from_config, stack, DummyAppliance


def pytest_addoption(parser):
    parser.addoption('--dummy-appliance', action='store_true')


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if config.getoption('--dummy-appliance'):
        appliance = DummyAppliance()
    else:
        appliance = load_appliances_from_config(conf.env)[0]
        appliance.set_session_timeout(86400)
    stack.push(appliance)
    plugin = ApplianceHolderPlugin(appliance)
    config.pluginmanager.register(plugin, "appliance-holder")


@pytest.hookimpl(trylast=True)
def pytest_unconfigure():
    stack.pop()


@attr.s(cmp=False)
class ApplianceHolderPlugin(object):
    held_appliance = attr.ib()

    @pytest.fixture(scope="session")
    def appliance(self):
        return self.held_appliance

    def pytest_sessionstart(self):
        if isinstance(self.held_appliance, DummyAppliance):
            return
        if pytest.store.parallelizer_role != 'slave':
            with log_path.join('appliance_version').open('w') as appliance_version:
                appliance_version.write(self.held_appliance.version.vstring)
