import pytest
from utils.appliance import ViaUI, ViaDB, current_appliance

from cfme.infrastructure.pxe import PXEServer


@pytest.fixture
def pxeserver():
    return PXEServer(name="John")


@pytest.mark.parametrize("endpoint", [ViaUI, ViaDB], ids=["ui", "db"])
def test_pxe_server_exist(endpoint, pxeserver):
    with current_appliance.sentaku_ctx.use(endpoint):
        assert not pxeserver.exists()
