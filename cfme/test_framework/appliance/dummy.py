import attr
import pytest

from cfme.fixtures import terminalreporter

from cfme.utils.appliance import DummyAppliance


PLUGIN_KEY = "dummy-appliance"
APP_TYPE = 'dummy'


def pytest_addoption(parser):
    group = parser.getgroup("appliances")
    group.addoption('--num-dummy-apps', default=10, type=int)


@pytest.hookimpl
def pytest_configure(config):
    app_types = config.getoption('--use-apps')
    if APP_TYPE in app_types:
        if len(app_types) > 1:
            raise ValueError("dummy appliances cannot be mixed with other types")

        reporter = terminalreporter.reporter()
        config.pluginmanager.register(DummyAppliancePlugin(), PLUGIN_KEY)
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
        holder.pools[APP_TYPE] = appliances


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    holder = config.pluginmanager.getplugin('appliance-holder')
    holder.stack.pop()


@attr.s(cmp=False)
class DummyAppliancePlugin(object):
    pass
