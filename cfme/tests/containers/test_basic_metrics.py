import pytest
import re
from cfme.containers.provider import ContainersProvider
from cfme.utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')]


@pytest.mark.polarion('CMP-10205')
def test_basic_metrics(provider):
    """ Basic Metrics availability test
        This test checks that the Metrics service is up
        Curls the hawkular status page and checks if it's up
        """
    routes = provider.mgmt.o_api.get('route')[1]['items']
    metrics_hostname = [route for route in routes
                        if route['metadata']['name'] == 'hawkular-metrics']
    assert metrics_hostname, 'Could not find route for hawkular-metrics'
    metrics_hostname = metrics_hostname.pop()['spec']['host']
    host_url = 'https://' + metrics_hostname + '/hawkular/metrics/'
    command = 'curl -X GET ' + host_url + ' --insecure'
    assert re.search("Hawkular[ -]Metrics", str(provider.cli.run_command(command)))
