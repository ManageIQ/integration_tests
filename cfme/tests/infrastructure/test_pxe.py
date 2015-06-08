import pytest

from cfme.infrastructure import pxe
from utils.update import update
from utils.testgen import generate, pxe_servers


pytest_generate_tests = generate(pxe_servers)


@pytest.fixture(scope='function')
def has_no_pxe_servers():
    pxe.remove_all_pxe_servers()


@pytest.mark.usefixtures('has_no_pxe_servers')
def test_pxe_server_crud(pxe_name, pxe_server_crud):
    """
    Basic Add test for PXE server including refresh.
    """
    pxe_server_crud.create(refresh_timeout=300)
    with update(pxe_server_crud):
        pxe_server_crud.name = pxe_server_crud.name + "_update"
    pxe_server_crud.delete(cancel=False)
