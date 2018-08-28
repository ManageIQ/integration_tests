import pytest
import requests

from cfme.containers.provider import ContainersProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider(gen_func=providers,
                         filters=[ProviderFilter(classes=[ContainersProvider],
                                                 required_flags=['metrics_collection'])],
                         scope='function')
]

TEST_ITEMS = ["containers_providers", "container_nodes"]


def get_test_object(appliance, provider, test_item):

    return (provider if test_item == "containers_providers" else
            getattr(appliance.collections, test_item).all().pop())


@pytest.fixture(scope="function")
def metrics_up_and_running(provider):

    try:
        router = [router for router in provider.mgmt.list_route()
                  if router.metadata.name == 'hawkular-metrics' or
                  router.metadata.name == 'prometheus'].pop()
        metrics_url = router.status.ingress[0].host
    except AttributeError:
        pytest.skip('Could not determine metric route for {}'.format(provider.key))
    creds = provider.get_credentials_from_config(provider.key, cred_type='token')
    header = {"Authorization": "Bearer {token}".format(token=creds.token)}
    response = requests.get("https://{url}:443".format(url=metrics_url), headers=header,
                            verify=False)
    assert response.ok, "{metrics} failed to start!".format(metrics=router.metadata.name)
    logger.info("{metrics} started successfully".format(metrics=router.metadata.name))


def is_ad_hoc_greyed(provider_object):
    view = navigate_to(provider_object, 'Details')
    return view.toolbar.monitoring.item_enabled('Ad hoc Metrics')


@pytest.mark.polarion('CMP-10643')
@pytest.mark.parametrize('test_item', TEST_ITEMS)
def test_ad_hoc_metrics_overview(appliance, provider, test_item, metrics_up_and_running):
    obj = get_test_object(appliance, provider, test_item)

    assert is_ad_hoc_greyed(obj), (
        "Monitoring --> Ad hoc Metrics not activated despite provider was set")


@pytest.mark.polarion('CMP-10645')
@pytest.mark.parametrize('test_item', TEST_ITEMS)
def test_ad_hoc_metrics_select_filter(appliance, provider, test_item, metrics_up_and_running):

    obj = get_test_object(appliance, provider, test_item)

    view = navigate_to(obj, 'AdHoc')
    view.wait_for_filter_option_to_load()
    view.set_filter(view.get_random_filter())
    view.apply_filter()
    view.wait_for_results_to_load()

    assert view.get_total_results_count() != 0, (
        "No results found for {filter}".format(filter=view.selected_filter))
