import fauxfactory
import pytest

from cfme.physical.provider.redfish import RedfishProvider
from cfme.utils.update import update

pytestmark = [
    pytest.mark.provider([RedfishProvider], scope="function")
]


def test_redfish_provider_crud(provider, has_no_physical_providers):
    """Tests provider add with good credentials

    Polarion:
        assignee: rhcf3_machine
        casecomponent: Infra
        initialEstimate: 1/4h
    """
    provider.create()

    provider.validate_stats(ui=True)

    old_name = provider.name
    with update(provider):
        provider.name = fauxfactory.gen_alphanumeric(8)  # random uuid

    with update(provider):
        provider.name = old_name  # old name

    provider.delete()
    provider.wait_for_delete()
