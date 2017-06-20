import pytest
from utils import testgen
from utils.log import logger
from cfme.containers.provider import ContainersProvider
from utils.version import current_version
from cfme.web_ui import toolbar
from utils.appliance.implementations.ui import navigate_to
from utils.wait import wait_for

pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.8"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


@pytest.fixture
def matrics_up_and_running(provider):
    import requests

    router = [router for router in provider.mgmt.o_api.get('route')[1]['items'] if
              router["metadata"]["name"] == "hawkular-metrics"].pop()
    hawkular_url = router["status"]["ingress"][0]["host"]
    response = requests.get("https://{url}:443".format(url=hawkular_url), verify=False)
    if not response.ok:
        raise Exception("hawkular failed to start!")
    logger.info("hawkular started successfully")


@pytest.fixture
def wait_for_metrics_population(provider):
    # in case of new provider was added wait for up to 25 minutes
    # for system to collect first metrics
    wait_for(lambda: provider.summary.status.last_metrics_collection.text_value != 'None',
             delay=60, num_sec=25 * 60)


def is_ad_hoc_greyed(provider_object):
    navigate_to(provider_object, 'Details')
    return toolbar.is_greyed('Monitoring', 'Ad hoc Metrics')


@pytest.mark.polarion('CMP-10643')
def test_ad_hoc_metrics_overview(provider,
                                 matrics_up_and_running):

    assert not is_ad_hoc_greyed(provider), \
        "Monitoring --> Ad hoc Metrics not activated despite provider was set"


@pytest.mark.polarion('CMP-10645')
def test_ad_hoc_metrics_select_filter(provider,
                                      matrics_up_and_running):

    view = navigate_to(provider, 'AdHoc')
    view.wait_for_filter_option_to_load()
    view.set_random_filter()
    view.apply_filter()
    view.wait_for_results_to_load()

    assert view.get_total_results_count() != 0,\
        "No results found for {filter}".format(filter=view.selected_filter)
