import pytest

from cfme.cloud.provider.azure import AzureProvider
from cfme.common.provider import BaseProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION


@pytest.mark.provider([AzureProvider], selector=ONE_PER_VERSION)
def test_provider_fixtures(provider, setup_provider):
    """Verify that clearing providers works correctly.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        initialEstimate: 1/15h
    """
    assert provider.exists, f"Provider {provider.name} not found on appliance."
    BaseProvider.clear_providers()
    assert not provider.exists, f"Provider {provider.name} not deleted from appliance."
