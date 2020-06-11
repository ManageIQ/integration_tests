import pytest

from cfme.cloud.provider.azure import AzureProvider
from cfme.common.provider import BaseProvider
from cfme.markers.env_markers.provider import ALL
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


@pytest.mark.provider([BaseProvider], selector=ALL)
def test_provider_all_selector(request, provider):
    """Verify that the 'all' selector works, and that the provider matches the parametrization."""
    expected_id = f"test_provider_all_selector[{provider.type}-{provider.version}-{provider.key}]"
    test_id = request.node.name
    assert test_id == expected_id, f"Provider parametrization failed."
