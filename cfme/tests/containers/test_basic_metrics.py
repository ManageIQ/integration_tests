import kubeshift
import requests
import pytest

from cfme.containers.provider import ContainersProvider
from utils import testgen
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

    os_api_url = "{0.rest_protocol}://{0.hostname}:{0.port}".format(
        provider.provider_data)

    # Prepare the creds for the kubeshift. Note we don't need to store
    # need to store the credentials in any file, hence /dev/null is used.
    # This means that the creds_name is also unimportant as it is thrown away.
    creds_name = "some-creds-identifier-that-doesnt't-mean-a-thing"
    kubeshift_config = kubeshift.Config.from_params(api=os_api_url,
                                                    verify=False,
                                                    filepath="/dev/null",
                                                    username=creds_name)
    kubeshift_config.set_credentials(creds_name,
                                     token=provider.credentials["token"].token)

    client = kubeshift.OpenshiftClient(kubeshift_config)
    hm_api = client.routes(namespace="openshift-infra").by_name("hawkular-metrics")["spec"]["host"]
    status_url = 'https://' + hm_api + '/hawkular/metrics/status'
    response = requests.get(status_url, verify=False)
    assert response.json().get("MetricsService") == "STARTED"
