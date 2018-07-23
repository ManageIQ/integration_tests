import pytest
import re

from cfme import test_requirements
from cfme.common.candu_views import UtilizationZoomView
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.c_and_u,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([VMwareProvider, RHEVMProvider, EC2Provider, AzureProvider],
                        scope='module',
                        required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')])
]

VM_GRAPHS = ['vm_cpu', 'vm_cpu_state', 'vm_memory', 'vm_disk', 'vm_network']
INTERVAL = ['Hourly', 'Daily']


# ToDo: Add support for GCE provider once BZ-1511099 fixed

# ToDo: Currently disk activity for EC2 not collecting due to infra issue.
# collect test as infra issue resolves.
@pytest.mark.uncollectif(lambda provider, graph_type:
                         ((provider.one_of(RHEVMProvider) or provider.one_of(AzureProvider)) and
                          graph_type == "vm_cpu_state") or
                         (provider.one_of(EC2Provider) and
                          graph_type in ["vm_cpu_state", "vm_memory", "vm_disk"]))
@pytest.mark.parametrize('graph_type', VM_GRAPHS)
def test_vm_most_recent_hour_graph_screen(graph_type, provider, enable_candu):
    """ Test VM graphs for most recent hour displayed or not

    prerequisites:
        * C&U enabled appliance

    Steps:
        * Navigate to VM (cu-24x7) Utilization Page
        * Check graph displayed or not
        * Check legends hide and display properly or not
        * Check data for legends collected or not
    """
    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.instantiate('cu-24x7', provider)
    vm.wait_candu_data_available(timeout=1200)

    view = navigate_to(vm, 'candu')
    view.options.interval.fill('Most Recent Hour')

    graph = getattr(view, graph_type)

    assert graph.is_displayed

    def refresh():
        provider.browser.refresh()
        view = navigate_to(vm, 'candu')
        view.options.interval.fill('Most Recent Hour')

    # wait, some time graph took time to load
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


def compare_data(tb_data, gp_data, legends, tolerance=1):
    """ Compare Utilization graph and table data.
    Args:
        tb_data : Data from Utilization table
        gp_data : Data from Utilization graph
        legends : Legends in graph; which will help for comparison
        tolerance : Its error which we have to allow while comparison
    """
    for row in tb_data:
        for key, data in gp_data.items():
            if any([re.match(key, item) for item in row['Date/Time'].split()]):
                for leg in legends:
                    tb = row[leg].replace(',', '').replace('%', '').split()
                    if tb:
                        tb = round(float(tb[0]), 1)
                        gp = round(
                            float(data[leg].replace(',', '').replace('%', '').split()[0]), 1)
                        assert abs(tb - gp) <= tolerance
                    else:
                        logger.warning("No {leg} data captured for DateTime: {dt}".format(
                            leg=leg, dt=row['Date/Time']))


@pytest.mark.uncollectif(lambda provider, interval, graph_type:
                         ((provider.one_of(RHEVMProvider) or provider.one_of(AzureProvider)) and
                          graph_type == "vm_cpu_state") or
                         (provider.one_of(EC2Provider) and
                          graph_type in ["vm_cpu_state", "vm_memory", "vm_disk"]) or
                         ((provider.one_of(CloudProvider) or provider.one_of(RHEVMProvider)) and
                         interval == 'Daily'))
@pytest.mark.parametrize('interval', INTERVAL)
@pytest.mark.parametrize('graph_type', VM_GRAPHS)
def test_graph_screen(provider, interval, graph_type, enable_candu):
    """Test VM graphs for hourly and Daily

    prerequisites:
        * C&U enabled appliance

    Steps:
        * Navigate to VM (cu-24x7) Utilization Page
        * Check graph displayed or not
        * Zoom graph
        * Compare data of Table and Graph
    """
    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.instantiate('cu-24x7', provider)

    if not provider.one_of(CloudProvider):
        wait_for(
            vm.capture_historical_data,
            delay=20,
            timeout=1000,
            message="wait for capturing VM historical data"
        )
    vm.wait_candu_data_available(timeout=1200)

    view = navigate_to(vm, 'candu')
    view.options.interval.fill(interval)

    graph = getattr(view, graph_type)
    assert graph.is_displayed

    def refresh():
        provider.browser.refresh()
        view = navigate_to(vm, 'candu')
        view.options.interval.fill(interval)

    # wait, some time graph took time to load
    wait_for(lambda: len(graph.all_legends) > 0,
             delay=5, timeout=600, fail_func=refresh)

    graph.zoom_in()
    view = view.browser.create_view(UtilizationZoomView)
    assert view.chart.is_displayed

    gp_data = view.chart.all_data
    # Clear cache of table widget before read else it will mismatch headers.
    view.table.clear_cache()
    tb_data = view.table.read()
    legends = view.chart.all_legends
    compare_data(tb_data=tb_data, gp_data=gp_data, legends=legends)
