# -*- coding: utf-8 -*-
import pytest
import subprocess

from utils.version import current_version
from utils.ssh import SSHClient


@pytest.fixture(scope="session")
def use_storage(uses_ssh):
    ssh_client = SSHClient()
    if ssh_client.appliance_has_netapp():
        return
    if not current_version().is_in_series("5.2"):
        pytest.skip("Storage tests run only on .2 so far")
    subprocess.call("python ./scripts/install_netapp_lib.py --restart", shell=True)
    subprocess.call("python ./scripts/wait_for_appliance_ui.py", shell=True)
    if not ssh_client.appliance_has_netapp():
        pytest.fail("Could not setup the netapp for storage testing")
