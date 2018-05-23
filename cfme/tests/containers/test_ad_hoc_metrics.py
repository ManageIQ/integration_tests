import pytest
import requests
from cfme.utils.log import logger
from cfme.containers.provider import ContainersProvider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')]


@pytest.fixture(scope="function")
def metrics_up_and_running(provider):

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
    logger.info("{metrics} started successfully".format(metrics=router["metadata"]["name"]))


def is_ad_hoc_greyed(provider_object):
    view = navigate_to(provider_object, 'Details')
    return view.toolbar.monitoring.item_enabled('Ad hoc Metrics')


@pytest.mark.polarion('CMP-10643')
def test_ad_hoc_metrics_overview(provider, metrics_up_and_running):

    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    assert is_ad_hoc_greyed(provider), (
        "Monitoring --> Ad hoc Metrics not activated despite provider was set")


@pytest.mark.polarion('CMP-10645')
def test_ad_hoc_metrics_select_filter(provider, metrics_up_and_running):

    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    view = navigate_to(provider, 'AdHoc')
    view.wait_for_filter_option_to_load()
    view.set_filter(view.get_random_filter())
    view.apply_filter()
    view.wait_for_results_to_load()

    assert view.get_total_results_count() != 0, (
        "No results found for {filter}".format(filter=view.selected_filter))
