import pytest

from cfme.infrastructure import pxe
from utils.randomness import generate_random_string
from utils.update import update
from utils.testgen import pxe_servers, generate

pytest_generate_tests = generate(pxe_servers, server_name='all')


@pytest.fixture(scope='function')
def has_no_pxe_servers():
    pxe.remove_all_pxe_servers()


@pytest.mark.usefixtures('has_no_pxe_servers')
def test_pxe_server_add(pxe_name, pxe_server_crud):
    """Basic default LDAP group role RBAC test

    Validates expected menu and submenu names are present for default
    LDAP group roles

    """
    pxe_server_crud.create()


@pytest.mark.usefixtures('has_no_pxe_servers')
def test_pxe_server_edit(pxe_name, pxe_server_crud):
    """Basic default LDAP group role RBAC test

    Validates expected menu and submenu names are present for default
    LDAP group roles

    """
    pxe_server_crud.create(refresh=False)
    with update(pxe_server_crud) as pxe_server_crud:
        pxe_server_crud.name = pxe_server_crud.name + "_update"


@pytest.mark.usefixtures('has_no_pxe_servers')
def test_pxe_server_delete(pxe_name, pxe_server_crud):
    """Basic default LDAP group role RBAC test

    Validates expected menu and submenu names are present for default
    LDAP group roles

    """
    pxe_server_crud.create(refresh=False)
    pxe_server_crud.delete(cancel=False)
