import pytest
from utils import testgen
from utils.log import logger
from cfme.containers.provider import ContainersProvider, navigate_and_get_rows, obj_factory
from utils.version import current_version
from cfme.web_ui import toolbar, tabstrip, form_buttons
from utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


def matrics_up_and_running(provider):
    import requests

    router = [router for router in provider.mgmt.o_api.get('route')[1]['items'] if
              router["metadata"]["name"] == "hawkular-metrics"].pop()
    hawkular_url = router["status"]["ingress"][0]["host"]
    response = requests.get("https://{url}:443".format(url=hawkular_url), verify=False)
    if not response.ok:
        raise Exception("hawkular failed to start!")
    logger.info("hawkular started successfully")

def set_hawkular_without_validation(provider_object):
    navigate_to(provider_object, 'Details')
    toolbar.select('Configurations', 'Edit this Containers Provider')
    tabstrip.select_tab("Hawkular")
    form_buttons.validate()

def navigate_to_ad_hoc_view(provider_object):
    navigate_to(provider_object, 'Details')
    toolbar.select('Monitoring', 'Ad hoc Metrics')


def is_ad_hoc_greyed(provider_object):
    navigate_to(provider_object, 'Details')
    return toolbar.is_greyed('Monitoring', 'Ad hoc Metrics')


#set_hawkular_without_validation(provider)

@pytest.mark.polarion('CMP-10643')
def test_ad_hoc_metrics_overview(provider):

    chosen_provider = navigate_and_get_rows(provider, ContainersProvider, 1).pop()
    provider_object = obj_factory(ContainersProvider, chosen_provider, provider)

    assert not is_ad_hoc_greyed(provider_object), \
        "Monitoring --> Ad hoc Metrics not activated despite provider was set"


@pytest.mark.polarion('CMP-10645')
def test_ad_hoc_metrics_select_filter(provider, appliance):

    chosen_provider = navigate_and_get_rows(provider, ContainersProvider, 1).pop()
    provider_object = obj_factory(ContainersProvider, chosen_provider, provider)

    view = navigate_to(provider_object, 'AdHoc')
    view.wait_for_filter_option_to_load()
    view.set_random_filter()
    view.apply_filter()
    view.wait_for_results_to_load()

    assert view.get_total_results_count() != 0,\
        "No results found for {filter}".format(filter=view.selected_filter)
