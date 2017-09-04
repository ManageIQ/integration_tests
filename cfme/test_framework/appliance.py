import attr
import pytest

from utils.appliance import get_or_create_current_appliance


def pytest_configure(config):
    appliance = get_or_create_current_appliance()
    appliance.set_session_timeout(86400)
    plugin = ApplianceHolderPlugin(appliance)
    config.pluginmanager.register(plugin, "appliance-holder")


@attr.s(cmp=False)
class ApplianceHolderPlugin(object):
    _appliance = attr.ib()

    @pytest.fixture(scope="session")
    def appliance(self):
        return self._appliance
