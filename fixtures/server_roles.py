from utils.appliance import set_server_roles_ui_workload
from utils.ssh import SSHClient
import pytest


@pytest.fixture(scope='session')
def set_server_roles_ui_workload_session():
    set_server_roles_ui_workload(SSHClient())
