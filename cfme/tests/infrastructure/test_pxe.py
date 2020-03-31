import pytest

from cfme import test_requirements
from cfme.infrastructure import pxe
from cfme.utils.testgen import generate
from cfme.utils.testgen import pxe_servers
from cfme.utils.update import update


pytest_generate_tests = generate(gen_func=pxe_servers)


@pytest.fixture(scope='function')
def has_no_pxe_servers():
    pxe.remove_all_pxe_servers()


@pytest.mark.tier(2)
@pytest.mark.usefixtures('has_no_pxe_servers')
@test_requirements.provision
def test_pxe_server_crud(pxe_name, pxe_server_crud):
    """
    Basic Add test for PXE server including refresh.

    Polarion:
        assignee: jhenner
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1/6h
        upstream: yes
    """
    pxe_server_crud.create(refresh_timeout=300)
    with update(pxe_server_crud):
        pxe_server_crud.name = f"{pxe_server_crud.name}_update"
    pxe_server_crud.delete(cancel=False)
