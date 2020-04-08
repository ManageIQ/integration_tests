import pytest

from cfme import test_requirements
from cfme.common.candu_views import UtilizationZoomView
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.tests.candu import compare_data
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.c_and_u,
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider(
        [VMwareProvider, RHEVMProvider],
        required_fields=[(["cap_and_util", "capandu_vm"], "cu-24x7")],
    ),
]

DATASTORE_GRAPHS = ["datastore_used_disk_space", "datastore_hosts", "datastore_vms"]

# To-Do: Add support for Daily. Datastore not support historical data collection
INTERVAL = ["Hourly"]


@pytest.mark.parametrize("interval", INTERVAL)
@pytest.mark.parametrize("graph_type", DATASTORE_GRAPHS)
def test_datastore_graph_screen(provider, interval, graph_type, enable_candu):
    """Test Datastore graphs for hourly

    prerequisites:
        * C&U enabled appliance

    Steps:
        * Navigate to Datastore Utilization Page
        * Check graph displayed or not
        * Select interval Hourly
        * Zoom graph to get Table
        * Compare table and graph data

    Polarion:
        assignee: gtalreja
        caseimportance: medium
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    vm_collection = provider.appliance.provider_based_collection(provider)
    vm = vm_collection.instantiate("cu-24x7", provider)
    datastore = vm.datastore

    datastore.wait_candu_data_available(timeout=1500)

    view = navigate_to(datastore, "Utilization")
    view.options.interval.fill(interval)

    # Check graph displayed or not
    try:
        graph = getattr(view.interval_type, graph_type)
    except AttributeError as e:
        logger.error(e)
    assert graph.is_displayed

    def refresh():
        provider.browser.refresh()
        view.options.interval.fill(interval)

    # wait, some time graph take time to load
    wait_for(lambda: bool(graph.all_legends), delay=5, timeout=200, fail_func=refresh)

    graph.zoom_in()
    view = view.browser.create_view(UtilizationZoomView)

    assert view.chart.is_displayed
    view.flush_widget_cache()
    legends = view.chart.all_legends
    graph_data = view.chart.all_data
    # Clear cache of table widget before read else it will mismatch headers.
    view.table.clear_cache()
    table_data = view.table.read()
    compare_data(table_data=table_data, graph_data=graph_data, legends=legends)
