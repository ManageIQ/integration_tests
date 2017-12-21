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


@pytest.mark.meta(blockers=[1200783])
def test_iso_datastore_crud(appliance, setup_provider, no_iso_dss, provider):
    """
    Basic CRUD test for ISO datastores.

    Note:
        An ISO datastore cannot be edited.

    Metadata:
        test_flag: iso
    """
    collection = appliance.collections.iso_datastores
    # template_crud = collection(provider.name)
    template_crud = collection.create(provider.name)
    template_crud.delete(cancel=False)
