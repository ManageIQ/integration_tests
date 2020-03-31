import pytest

from cfme import test_requirements
from cfme.infrastructure import pxe
from cfme.infrastructure.provider import InfraProvider


pytestmark = [
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.tier(2),
    pytest.mark.provider([InfraProvider], required_fields=[('iso_datastore', True)]),
]


@pytest.fixture()
def no_iso_dss(provider):
    template_crud = pxe.ISODatastore(provider.name)
    if template_crud.exists():
        template_crud.delete(cancel=False)


@test_requirements.rhev
def test_iso_datastore_crud(setup_provider, no_iso_dss, provider):
    """
    Basic CRUD test for ISO datastores.

    Note:
        An ISO datastore cannot be edited.

    Metadata:
        test_flag: iso

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Infra
        caseimportance: critical
    """
    template_crud = pxe.ISODatastore(provider.name)
    template_crud.create()
    template_crud.delete(cancel=False)
