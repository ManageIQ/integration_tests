import pytest

from cfme.infrastructure import pxe
from cfme.infrastructure.provider import InfraProvider


pytestmark = [
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.tier(2),
    pytest.mark.provider([InfraProvider], required_fields=['iso_datastore']),
]


@pytest.fixture()
def no_iso_dss(provider):
    template_crud = pxe.ISODatastore(provider.name)
    if template_crud.exists():
        template_crud.delete(cancel=False)


@pytest.mark.rhv1
@pytest.mark.meta(blockers=[1200783])
def test_iso_datastore_crud(setup_provider, no_iso_dss, provider):
    """
    Basic CRUD test for ISO datastores.

    Note:
        An ISO datastore cannot be edited.

    Metadata:
        test_flag: iso

    Polarion:
        assignee: None
        initialEstimate: None
    """
    template_crud = pxe.ISODatastore(provider.name)
    template_crud.create()
    template_crud.delete(cancel=False)
