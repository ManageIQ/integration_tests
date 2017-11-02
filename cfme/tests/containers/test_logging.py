import pytest

from cfme.utils.version import current_version
from cfme.utils.appliance.implementations.ui import navigate_to

from cfme.containers.provider import ContainersProvider, ContainersTestItem

NUM_OF_DEFAULT_LOG_ROUTES = 2
pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.8"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')]


TEST_ITEMS = [
    pytest.mark.polarion('CMP-10634')(ContainersTestItem(ContainersProvider, 'CMP-10634'))
    # TODO Add Node back into the list when other classes are updated to use WT views and widgets.
    # pytest.mark.polarion('CMP-10635')(ContainersTestItem(Node, 'CMP-10635'))
]


@pytest.fixture(scope="function")
def logging_routes(provider):
    routers = [router for router in provider.mgmt.o_api.get('route')[1]['items']
               if "logging" in router["metadata"]["name"]]

    all_routers_up = all([router["status"]["ingress"][0]["conditions"][0]["status"]
                          for router in routers])

    all_pods = {pod: status["Ready"]
                for pod, status in provider.pods_per_ready_status().iteritems() if "logging" in pod}

    assert all_pods, "no logging pods found"
    assert all(all_pods), "some pods not ready"
    assert len(routers) <= NUM_OF_DEFAULT_LOG_ROUTES, "some logging route is missing"
    assert all_routers_up, "some logging route is off"

    return routers


def get_ose_logging_url(logging_routes):
    ops_router = [router for router in logging_routes
                  if "logging-kibana-ops" in router["metadata"]["name"]].pop()
    return ops_router['status']['ingress'][0]['host']


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ContainersTestItem.get_pretty_id(ti) for ti in TEST_ITEMS])
def test_external_logging_activated(provider, appliance, test_item):

    if test_item.obj is ContainersProvider:
        obj_inst = provider
    else:
        obj_inst = test_item.obj.get_random_instances(provider, 1, appliance).pop()

    view = navigate_to(obj_inst, 'Details')
    assert view.monitor.item_enabled('External Logging'), (
        "Monitoring --> External Logging not activated")

    cfme_logging_url = "https://{url}".format(url=view.get_logging_url())
    ose_logging_url = get_ose_logging_url(logging_routes(provider))
    assert ose_logging_url in cfme_logging_url, "CFME loggging address is invalid"
