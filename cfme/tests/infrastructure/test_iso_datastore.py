import pytest

from cfme.infrastructure import pxe
from utils import testgen

pytestmark = [
    pytest.mark.usefixtures("logged_in"),
    pytest.mark.usefixtures('uses_infra_providers'),
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, 'iso_datastore')

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['iso_datastore']:
            # No provisioning data available
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture()
def no_iso_dss(provider):
    template_crud = pxe.ISODatastore(provider.name)
    if template_crud.exists():
        template_crud.delete(cancel=False)


@pytest.mark.meta(blockers=[1200783])
def test_iso_datastore_crud(setup_provider, no_iso_dss, provider, iso_datastore):
    """
    Basic CRUD test for ISO datastores.

    Note:
        An ISO datastore cannot be edited.

    Metadata:
        test_flag: iso
    """
    template_crud = pxe.ISODatastore(provider.name)
    template_crud.create()
    template_crud.delete(cancel=False)
