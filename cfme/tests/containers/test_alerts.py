import pytest

from cfme.containers.provider import ContainersProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.version import current_version
from cfme.utils.providers import ProviderFilter


pytestmark = [
    pytest.mark.provider(classes=[ContainersProvider], required_flags=['prometheus_alerts'])
]

# TODO There needs to be more to this test


def test_add_alerts_provider(provider):
    """
    Polarion:
        assignee: juwatts
        initialEstimate: 1/4h
        caseimportance: low
        casecomponent: Containers
    """
    provider.setup()
