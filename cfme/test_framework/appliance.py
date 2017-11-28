import attr
import pytest
import warnings

from fixtures import terminalreporter
from cfme.utils import conf

from cfme.utils.path import log_path
from cfme.utils.appliance import (
    load_appliances_from_config, stack,
    DummyAppliance, IPAppliance,
    ApplianceSummoningWarning)

warnings.simplefilter('error', ApplianceSummoningWarning)


def pytest_addoption(parser):
    parser.addoption('--dummy-appliance', action='store_true')
    parser.addoption('--dummy-appliance-version', default=None)


def appliances_from_cli(cli_appliances):
    appliance_config = {'appliances': [
        {'base_url': base_url} for base_url in cli_appliances]}
    # Grab the possible globals from the conf.env
    for key, value in (
            (key, value)
            for key, value in conf.env.items()
            if key in IPAppliance.CONFIG_MAPPING and key not in IPAppliance.CONFIG_NONGLOBAL):
        appliance_config[key] = value
    return load_appliances_from_config(appliance_config)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):

    reporter = terminalreporter.reporter()
    if stack.top:
        appliances = [stack.top]
    elif config.getoption('--dummy-appliance'):
        appliances = [DummyAppliance.from_config(config)]
        reporter.write_line('Retrieved Dummy Appliance', red=True)
    elif config.option.appliances:
        appliances = appliances_from_cli(config.option.appliances)
        reporter.write_line('Retrieved these appliances from the --appliance parameters', red=True)
    elif config.getoption('--use-sprout'):
        from .sprout.plugin import mangle_in_sprout_appliances
        mangle_in_sprout_appliances(config)
        appliances = appliances_from_cli(config.option.appliances)
        reporter.write_line('Retrieved these appliances from the --sprout-* parameters', red=True)
    else:
        appliances = load_appliances_from_config(conf.env)
        reporter.write_line('Retrieved these appliances from the conf.env', red=True)

    if not stack.top:
        for appliance in appliances:
            reporter.write_line('* {!r}'.format(appliance), cyan=True)
    appliance = appliances[0]
    appliance.set_session_timeout(86400)
    stack.push(appliance)
    plugin = ApplianceHolderPlugin(appliance, appliances)
    config.pluginmanager.register(plugin, "appliance-holder")


@pytest.hookimpl(trylast=True)
def pytest_unconfigure():
    stack.pop()


@attr.s(cmp=False)
class ApplianceHolderPlugin(object):
    held_appliance = attr.ib()
    appliances = attr.ib(default=attr.Factory(list))

    @pytest.fixture(scope="session")
    def appliance(self):
        return self.held_appliance

    def pytest_sessionstart(self):
        if isinstance(self.held_appliance, DummyAppliance):
            return
        if pytest.store.parallelizer_role != 'slave':
            with log_path.join('appliance_version').open('w') as appliance_version:
                appliance_version.write(self.held_appliance.version.vstring)
