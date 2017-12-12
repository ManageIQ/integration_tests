import pytest

from cfme.infrastructure.pxe import get_pxe_server_from_config


@pytest.fixture
def pxe_server_crud(appliance, pxe_name):
    return get_pxe_server_from_config(pxe_name, appliance=appliance)
