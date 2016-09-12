import pytest
import cfme.fixtures.pytest_selenium as sel
from utils import testgen
from utils.browser import ensure_browser_open
from utils import conf
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
    hostname = 'https://' + conf.cfme_data.get('management_systems', {})[provider.key]\
        .get('hostname', []) + '/hawkular/metrics'
    ensure_browser_open()
    sel.get(hostname)
    element = sel.elements('//*[contains(., "STARTED")]')
    assert element
