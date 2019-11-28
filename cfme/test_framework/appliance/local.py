import attr
import pytest
import sys

from cfme.fixtures import terminalreporter

PLUGIN_KEY = "local-appliance"
APP_TYPE = 'local'


@pytest.hookimpl
def pytest_configure(config):
    if config.getoption('--help'):
        return
    reporter = terminalreporter.reporter()

    if config.getoption('--use-local-apps'):
        if config.getoption('--use-dummy-apps'):
            # TODO: use subparser or mutually exclusive group instead
            reporter.write_line('dummy appliances cannot be mixed with local appliance', red=True)
            sys.exit(5)

        plugin = LocalAppliancePlugin()
        config.pluginmanager.register(plugin, PLUGIN_KEY)

        from cfme.utils.appliance import IPAppliance
        appliances = [IPAppliance.from_url('https://127.0.0.1')]

        reporter.write_line('Retrieved Local Appliance', red=True)
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
class LocalAppliancePlugin(object):
    pass
