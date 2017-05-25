import pytest
from utils import testgen
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
        raise Exception("hawkular failed started!")
    print "hawkular started successfully"


def set_hawkular_without_validation(provider_object):
    navigate_to(provider_object, 'Details')
    toolbar.select('Configurations', 'Edit this Containers Provider')
    tabstrip.select_tab("Hawkular")
    form_buttons.validate()


def navigate_to_ad_hoc_page(provider_object):
    navigate_to(provider_object, 'Details')
    is_greyed = toolbar.is_greyed('Monitoring', 'Ad hoc Metrics')
    assert not is_greyed, "Monitoring --> Ad hoc Metrics not activated despite provider was set"


@pytest.mark.polarion('CMP-10643')
def test_ad_hoc_metrics_overview(provider):
    matrics_up_and_running(provider)

    chosen_provider = navigate_and_get_rows(provider, ContainersProvider, 1).pop()
    provider_object = obj_factory(ContainersProvider, chosen_provider, provider)

    # TODO: replace with pavelz code if marged
    set_hawkular_without_validation(provider_object)

    navigate_to_ad_hoc_page(provider_object)


@pytest.mark.polarion('CMP-10645')
def test_ad_hoc_metrics_select_filter(provider):
    matrics_up_and_running(provider)

    chosen_provider = navigate_and_get_rows(provider, ContainersProvider, 1).pop()
    provider_object = obj_factory(ContainersProvider, chosen_provider, provider)

    # TODO: replace with pavelz code if marged
    set_hawkular_without_validation(provider_object)

    navigate_to_ad_hoc_page(provider_object)

    # TODO: implementat for steps of entering a filter by pressing the button
