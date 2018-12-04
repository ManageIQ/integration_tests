import pytest

from cfme.containers.provider import ContainersProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.version import current_version
from cfme.utils.providers import ProviderFilter


pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() < "5.9"),
    pytest.mark.provider(gen_func=providers,
                         filters=[ProviderFilter(classes=[ContainersProvider],
                                                 required_flags=['prometheus_alerts'])],
                         scope='function')
]

# TODO There needs to be more to this test


def test_add_alerts_provider(provider):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    provider.setup()
