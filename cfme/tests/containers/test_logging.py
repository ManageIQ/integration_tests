import pytest

from cfme.containers.provider import ContainersProvider, ContainersTestItem
from cfme.containers.node import Node, NodeCollection
from cfme.markers.env_markers.provider import providers
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.providers import ProviderFilter
from cfme.utils.version import current_version

NUM_OF_DEFAULT_LOG_ROUTES = 2
pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.8"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider(gen_func=providers,
                         filters=[ProviderFilter(classes=[ContainersProvider],
                                                 required_flags=['cmqe_logging'])],
                         scope='function')]

TEST_ITEMS = [
    pytest.mark.polarion('CMP-10634')(ContainersTestItem(
        ContainersProvider, 'CMP-10634', collection_obj=None)),
    pytest.mark.polarion('CMP-10635')(ContainersTestItem(
        Node, 'CMP-10635', collection_obj=NodeCollection))
]


@pytest.fixture(scope="function")
def logging_routes(provider):
    routers = [router for router in provider.mgmt.o_api.get('route')[1]['items']
               if "logging" in router["metadata"]["name"]]

    all_routers_up = all([router["status"]["ingress"][0]["conditions"][0]["status"]
                          for router in routers])

    all_pods = {pod: status["Ready"]
                for pod, status in provider.pods_per_ready_status().items() if "logging" in pod}

    assert all_pods, "no logging pods found"
    assert all(all_pods.values()), "some pods not ready"
    assert len(routers) >= NUM_OF_DEFAULT_LOG_ROUTES, "some logging route is missing"
    assert all_routers_up, "some logging route is off"

    return routers


@pytest.fixture(scope="function")
def get_ose_logging_url(logging_routes):
    ops_router = [router for router in logging_routes
                  if "logging-kibana-ops" in router["metadata"]["name"]].pop()
    return ops_router['status']['ingress'][0]['host']


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ContainersTestItem.get_pretty_id(ti) for ti in TEST_ITEMS])
def test_external_logging_activated(provider, appliance, test_item, get_ose_logging_url):

    if test_item.obj is ContainersProvider:
        obj_inst = provider
    else:
        obj_inst = test_item.collection_obj(appliance).all()[0]

    view = navigate_to(obj_inst, 'Details')
    assert view.toolbar.monitoring.item_enabled('External Logging'), (
        "Monitoring --> External Logging not activated")

    cfme_logging_url = "https://{url}".format(url=view.get_logging_url())
    assert get_ose_logging_url in cfme_logging_url, "CFME loggging address is invalid"
