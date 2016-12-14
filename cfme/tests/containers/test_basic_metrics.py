import pytest
import re
from cfme.containers.provider import ContainersProvider
from utils import testgen
from utils import conf
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


def test_basic_metrics(provider, ssh_client):
    """ Basic Metrics availability test
        This test checks that the Metrics service is up
        Curls the hawkular status page and checks if it's up
        """
    username, password = provider.credentials['token'].principal,\
        provider.credentials['token'].secret
    hostname = conf.cfme_data.get('management_systems', {})[provider.key]\
        .get('hostname', [])
    host_url = 'https://' + hostname + '/hawkular/metrics/'
    command = 'curl -X GET ' + host_url + ' --insecure'
    ssh_client = ssh_client(hostname=hostname, username=username, password=password)
    assert re.search("Hawkular[ -]Metrics", str(ssh_client.run_command(command)))
