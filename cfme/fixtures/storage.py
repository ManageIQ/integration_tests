# -*- coding: utf-8 -*-
import pytest

from fixtures.pytest_store import store

from utils.version import current_version


@pytest.fixture(scope="function")
def use_storage(uses_ssh):
    appliance = store.current_appliance
    if appliance.has_netapp:
        return
    # TODO: Should this now say is greater than 5.2?
    if not current_version().is_in_series("5.2"):
        pytest.skip("Storage tests run only on .2 so far")

    appliance.install_netapp_sdk(reboot=True)
    if not appliance.has_netapp:
        pytest.fail("Could not setup the netapp for storage testing")
