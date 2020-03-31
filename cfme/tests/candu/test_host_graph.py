import pytest

from cfme import test_requirements
from cfme.common.candu_views import UtilizationZoomView
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.tests.candu import compare_data
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.c_and_u,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([VMwareProvider, RHEVMProvider], selector=ONE_PER_TYPE,
                         required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')]),
]


HOST_RECENT_HR_GRAPHS = ['host_cpu',
                         'host_memory',
                         'host_disk',
                         'host_network']

HOST_GRAPHS = ['host_cpu',
               'host_memory',
               'host_disk',
               'host_network',
               'host_cpu_state']

INTERVAL = ['Hourly', 'Daily']

GROUP_BY = ['VM Location']


@pytest.fixture(scope='function')
def host(appliance, provider):
    collection = appliance.collections.hosts
    for test_host in provider.data['hosts']:
        if not test_host.get('test_fleece', False):
            continue
        return collection.instantiate(name=test_host.name, provider=provider)


@pytest.mark.uncollectif(lambda provider, graph_type:
                         provider.one_of(RHEVMProvider) and graph_type == "host_disk",
                         reason='host_disk graph type not supported on RHEVM')
@pytest.mark.parametrize('graph_type', HOST_RECENT_HR_GRAPHS)
def test_host_most_recent_hour_graph_screen(graph_type, provider, host, enable_candu):
    """ Test Host graphs for most recent hour displayed or not

    prerequisites:
        * C&U enabled appliance

    Steps:
        * Navigate to Host Utilization Page
        * Check graph displayed or not
        * Check legends hide and display properly or not
        * Check data for legends collected or not

    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: CandU
    """

    host.wait_candu_data_available(timeout=1200)

    view = navigate_to(host, 'candu')
    view.options.interval.fill('Most Recent Hour')

    graph = getattr(view.interval_type, graph_type)

    assert graph.is_displayed

    def refresh():
        provider.browser.refresh()
        view.options.interval.fill('Most Recent Hour')

    # wait, some time graph take time to load
    wait_for(lambda: len(graph.all_legends) > 0,
             delay=5, timeout=600, fail_func=refresh)

    # Check for legend hide property and graph data
    graph_data = 0
    for leg in graph.all_legends:
        # check legend hide or not
        graph.hide_legends(leg)
        assert not graph.legend_is_displayed(leg)

        # check legend display or not
        graph.display_legends(leg)
        assert graph.legend_is_displayed(leg)

        # check graph display data or not
        # Note: legend like %Ready have less value some time zero. so sum data for all legend
        for data in graph.data_for_legends(leg).values():
            graph_data += float(data[leg].replace(',', '').replace('%', '').split()[0])
    assert graph_data > 0


@pytest.mark.uncollectif(lambda provider, graph_type:
                         provider.one_of(RHEVMProvider) and graph_type == "host_disk",
                         reason='host_disk graph type not supported on RHEVM')
@pytest.mark.parametrize('interval', INTERVAL)
@pytest.mark.parametrize('graph_type', HOST_GRAPHS)
def test_host_graph_screen(provider, interval, graph_type, host, enable_candu):
    """Test Host graphs for hourly and Daily

    prerequisites:
        * C&U enabled appliance

    Steps:
        * Navigate to Host Utilization Page
        * Check graph displayed or not
        * Select interval(Hourly or Daily)
        * Zoom graph to get Table
        * Compare table and graph data

    Polarion:
        assignee: nachandr
        caseimportance: medium
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    wait_for(
        host.capture_historical_data,
        delay=20,
        timeout=1000,
        message="wait for capturing host historical data")
    host.wait_candu_data_available(timeout=1200)

    view = navigate_to(host, 'candu')
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
    wait_for(lambda: len(graph.all_legends) > 0,
             delay=5, timeout=200, fail_func=refresh)

    # zoom in button not available with normal graph in Host Utilization page.
    # We have to use vm average graph for zoom in operation.
    try:
        vm_avg_graph = getattr(view.interval_type, f"{graph_type}_vm_avg")
    except AttributeError as e:
        logger.error(e)
    vm_avg_graph.zoom_in()
    view = view.browser.create_view(UtilizationZoomView)

    # wait, some time graph take time to load
    wait_for(lambda: len(view.chart.all_legends) > 0,
             delay=5, timeout=300, fail_func=refresh)
    assert view.chart.is_displayed
    view.flush_widget_cache()
    legends = view.chart.all_legends
    graph_data = view.chart.all_data
    # Clear cache of table widget before read else it will mismatch headers.
    view.table.clear_cache()
    table_data = view.table.read()
    compare_data(table_data=table_data, graph_data=graph_data, legends=legends)
