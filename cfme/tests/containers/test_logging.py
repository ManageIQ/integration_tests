import pytest

from utils import testgen
from utils.version import current_version
from utils.appliance.implementations.ui import navigate_to

from cfme.containers.provider import ContainersProvider

NUM_OF_DEFAULT_LOG_ROUTES = 2
pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.8"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


@pytest.fixture(scope="function")
def logging_routes(provider):
    routers = [router for router in provider.mgmt.o_api.get('route')[1]['items']
               if "logging" in router["metadata"]["name"]]
    all_routers_up = all([router["status"]["ingress"][0]["conditions"][0]["status"]
                          for router in routers])

    assert len(routers) <= NUM_OF_DEFAULT_LOG_ROUTES, "some logging route is missing"
    assert all_routers_up, "some logging route is off"

    return routers


def get_ose_logging_url(logging_routes):
    ops_router = [router for router in logging_routes
                  if "logging-kibana-ops" in router["metadata"]["name"]].pop()
    return ops_router['status']['ingress'][0]['host']


@pytest.mark.polarion('CMP-10634')
def test_external_logging_activated(provider):
    view = navigate_to(provider, 'Details')
    assert view.monitor.item_enabled('External Logging'), (
        "Monitoring --> External Logging not activated")

    cfme_logging_url = "https://{url}".format(url=view.get_logging_url())
    ose_logging_url = get_ose_logging_url(logging_routes(provider))
    assert ose_logging_url in cfme_logging_url, "CFME loggging address is invalid"
