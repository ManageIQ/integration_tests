import pytest
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.6"),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')


def test_basic_metrics(provider):
    """ Basic Metrics availability test
        This test checks that the Metrics service is up
        Opens the hawkular status page and checks if it's up
        """
    assert provider.check_metrics(provider)
