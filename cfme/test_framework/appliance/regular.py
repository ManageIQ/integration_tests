import attr
import pytest

from cfme.fixtures import terminalreporter

PLUGIN_KEY = "regular-appliance"
APP_TYPE = "regular"


def pytest_addoption(parser):
    group = parser.getgroup("appliances")

    # regular appliance type
    group.addoption('--num-regular-apps', action=1, type=int)


@pytest.hookimpl
def pytest_configure(config):
    app_types = config.getoption('--use-apps')
    if APP_TYPE in app_types:
        reporter = terminalreporter.reporter()

        plugin = RegularAppliancePlugin()
        config.pluginmanager.register(plugin, PLUGIN_KEY)

        from cfme.test_framework.sprout.plugin import mangle_in_sprout_appliances
        mangle_in_sprout_appliances(config)
        # TODO : handle direct sprout pass on?
        appliances = appliances_from_cli(config.option.appliances, None)

        appliances = [
            DummyAppliance.from_config(config) for _ in range(config.getoption('--num-dummy-apps'))
        ]
        reporter.write_line('Retrieved Dummy Appliances', red=True)
        reporter.write_line('Retrieved these appliances from the --sprout-* parameters', red=True)

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
class RegularAppliancePlugin(object):
    pass
