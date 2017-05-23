import pytest
import re
from cfme.containers.provider import ContainersProvider
from utils import testgen
from utils import conf
import httplib
from utils.ssh import SSHClient
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')

def access_https(url):
    c = httplib.HTTPSConnection(url)
    c.request("GET", "/")
    response = c.getresponse()
    data = response.read()
    status = response.status
    return {"status": status, "data": data}

def matrics_up_and_running(provider):
        routers = [router for router in provider.mgmt.o_api.get('route')[1]['items'] if
                   router["metadata"]["name"] == "hawkular-metrics"]
        hawkular_urls = [router["status"]["ingress"][0]["host"] for router in routers]
        responses = [access_https(url) for url in hawkular_urls]
        if not all(["A time series metrics engine based on Cassandra" in response.get("data") and
                    response.get("status") == 200 for response in responses]):
            raise Exception("matrices not started")
        print "Matrix started successfully"

@pytest.mark.polarion('CMP-10643')
def test_ad_hoc_metrics_overview(provider):
    pass

@pytest.mark.polarion('CMP-10645')
def test_ad_hoc_metrics_select_filter(provider):
    pass

