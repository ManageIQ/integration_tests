import attr
import pytest

from cfme.fixtures import terminalreporter

from cfme.utils.appliance import DummyAppliance


PLUGIN_KEY = "dummy-appliance"


def pytest_addoption(parser):
    group = parser.getgroup("cfme")

    # dummy appliance type
    group.addoption('--use-dummy-apps', action='store_true', default=False)
    group.addoption('--num-dummy-apps', default=1, type=int)


@pytest.hookimpl
def pytest_configure(config):
    if config.getoption('--help'):
        return
    reporter = terminalreporter.reporter()

    if config.getoption('--use-dummy-apps'):
        plugin = DummyAppliancePlugin()
        config.pluginmanager.register(plugin, PLUGIN_KEY)
        appliances = [
            DummyAppliance.from_config(config) for _ in range(config.getoption('--num-dummy-apps'))
        ]
        reporter.write_line('Retrieved Dummy Appliances', red=True)
        reporter.write_line('Retrieved these appliances from the --sprout-* parameters', red=True)

        holder = config.pluginmanager.getplugin('appliance-holder')

        for appliance in appliances:
            reporter.write_line('* {!r}'.format(appliance), cyan=True)

        holder.stack.push(appliances[0])
        holder.held_appliance = appliances[0]
        holder.appliances = appliances


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    holder = config.pluginmanager.getplugin('appliance-holder')
    holder.stack.pop()


@attr.s(cmp=False)
class DummyAppliancePlugin(object):
    pass
