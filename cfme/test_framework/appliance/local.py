import attr
import pytest

from cfme.fixtures import terminalreporter
from cfme.utils.appliance import DevAppliance

PLUGIN_KEY = "local-appliance"
APP_TYPE = DevAppliance.type


@pytest.hookimpl
def pytest_configure(config):
    app_type = config.getoption('--app-type')
    if APP_TYPE == app_type:
        reporter = terminalreporter.reporter()

        plugin = LocalAppliancePlugin()
        config.pluginmanager.register(plugin, PLUGIN_KEY)

        from cfme.utils.appliance import DevAppliance
        appliances = [DevAppliance.from_url('https://127.0.0.1')]

        reporter.write_line('Retrieved Local Appliance', red=True)
        for appliance in appliances:
            reporter.write_line(f'* {appliance!r}', cyan=True)

        holder = config.pluginmanager.getplugin('appliance-holder')
        holder.stack.push(appliances[0])
        holder.held_appliance = appliances[0]
        holder.pool = appliances


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    app_type = config.getoption('--app-type')
    if APP_TYPE == app_type:
        holder = config.pluginmanager.getplugin('appliance-holder')
        holder.stack.pop()


@attr.s(eq=False)
class LocalAppliancePlugin:
    pass
