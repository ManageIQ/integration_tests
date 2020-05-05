import attr
import pytest

from cfme.fixtures import terminalreporter
from cfme.utils.appliance import DummyAppliance


PLUGIN_KEY = "dummy-appliance"
APP_TYPE = DummyAppliance.type


@pytest.hookimpl
def pytest_configure(config):
    app_type = config.getoption('--app-type')
    if APP_TYPE == app_type:
        reporter = terminalreporter.reporter()
        if not config.option.collectonly:
            config.option.collectonly = True

        config.pluginmanager.register(DummyAppliancePlugin(), PLUGIN_KEY)
        appliances = [
            DummyAppliance.from_config(config) for _ in range(config.getoption('--app-num'))
        ]
        reporter.write_line('Retrieved Dummy Appliances', red=True)
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
class DummyAppliancePlugin:
    pass
