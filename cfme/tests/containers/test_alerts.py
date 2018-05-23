import pytest

from cfme.containers.provider import ContainersProvider
from cfme.utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() < "5.9"),
    pytest.mark.provider([ContainersProvider], scope='module')
]


@pytest.fixture
def ensure_alerts(provider):
    if 'alerts' not in provider.endpoints:
        pytest.skip('No alerts endpoint found for this provider')


def test_add_alerts_provider(ensure_alerts, provider):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    provider.setup()
