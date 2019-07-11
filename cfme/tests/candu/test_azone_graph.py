import pytest

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.common.candu_views import UtilizationZoomView
from cfme.tests.candu import compare_data
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.c_and_u,
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider(
        [AzureProvider, EC2Provider, GCEProvider],
        required_fields=[["cap_and_util", "capandu_azone"]],
    ),
]


GRAPHS = ["azone_cpu", "azone_memory", "azone_disk", "azone_network", "azone_instance"]

# To-Do: Add support for Daily interval
INTERVAL = ["Hourly"]


@pytest.fixture(scope="function")
def azone(appliance, provider):
    collection = appliance.collections.cloud_av_zones
    azone_name = provider.data["cap_and_util"]["capandu_azone"]
    return collection.instantiate(name=azone_name, provider=provider)


@pytest.mark.parametrize("interval", INTERVAL)
@pytest.mark.parametrize("graph_type", GRAPHS)
@pytest.mark.meta(
    blockers=[BZ(1671580, unblock=lambda provider: not provider.one_of(AzureProvider))]
)
@pytest.mark.uncollectif(lambda provider, graph_type: provider.one_of(EC2Provider)
    and graph_type == "azone_disk")
def test_azone_graph_screen(provider, azone, graph_type, interval, enable_candu):
    """Test Availibility zone graphs for Hourly

    prerequisites:
        * C&U enabled appliance

    Steps:
        * Navigate to Availibility Zone Utilization Page
        * Check graph displayed or not
        * Select interval Hourly
        * Zoom graph to get Table
        * Compare table and graph data

    Polarion:
        assignee: nachandr
        caseimportance: medium
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    azone.wait_candu_data_available(timeout=1200)

    view = navigate_to(azone, "Utilization")
    view.options.interval.fill(interval)

    # Check graph displayed or not
    try:
        graph = getattr(view, graph_type)
    except AttributeError as e:
        logger.error(e)
    assert graph.is_displayed

    def refresh():
        provider.browser.refresh()
        view.options.interval.fill(interval)

    # wait, some time graph take time to load
    wait_for(lambda: len(graph.all_legends) > 0, delay=5, timeout=200, fail_func=refresh)

    # zoom in button not available with normal graph except Instance in Azone Utilization page.
    # We have to use vm average graph for zoom in operation.
    avg_graph = graph_type if graph_type == "azone_instance" else "{}_avg".format(graph_type)
    try:
        avg_graph = getattr(view, avg_graph)
    except AttributeError as e:
        logger.error(e)
    avg_graph.zoom_in()
    view = view.browser.create_view(UtilizationZoomView)

    # wait, some time graph take time to load
    wait_for(lambda: len(view.chart.all_legends) > 0, delay=5, timeout=300, fail_func=refresh)
    assert view.chart.is_displayed
    view.flush_widget_cache()
    legends = view.chart.all_legends
    graph_data = view.chart.all_data
    # Clear cache of table widget before read else it will mismatch headers.
    view.table.clear_cache()
    table_data = view.table.read()
    compare_data(table_data=table_data, graph_data=graph_data, legends=legends)
