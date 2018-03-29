import pytest
import requests
from cfme.containers.provider import ContainersProvider


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')]

# TODO This test needs to be reevaluated. This is not testing anyting in CFME.


@pytest.mark.polarion('CMP-10205')
def test_basic_metrics(provider):
    """ Basic Metrics availability test
        This test checks that the Metrics service is up
        Curls the hawkular status page and checks if it's up
        """
    try:
        router = [router for router in provider.mgmt.o_api.get('route')[1]['items']
                  if router["metadata"]["name"] == 'hawkular-metrics' or
                  router["metadata"]["name"] == 'prometheus'].pop()
    except IndexError:
        pytest.skip('No Metrics Route available for {}'.format(provider.key))
    metrics_url = router["status"]["ingress"][0]["host"]
    creds = provider.get_credentials_from_config(provider.key, cred_type='token')
    header = {"Authorization": "Bearer {token}".format(token=creds.token)}
    response = requests.get("https://{url}:443".format(url=metrics_url), headers=header,
                            verify=False)
    assert response.ok, "{metrics} failed to start!".format(metrics=router["metadata"]["name"])
