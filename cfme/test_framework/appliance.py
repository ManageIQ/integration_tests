import attr
import pytest

from cfme.utils import conf

from cfme.utils.appliance import load_appliances_from_config, stack


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):

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
    _appliance = attr.ib()

    @pytest.fixture(scope="session")
    def appliance(self):
        return self._appliance
