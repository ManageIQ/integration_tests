import pytest

from cfme import test_requirements
from cfme.common.vm import VM
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.c_and_u,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([VMwareProvider, RHEVMProvider, EC2Provider, AzureProvider],
                         required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')])
]

VM_GRAPHS = ['vm_cpu', 'vm_cpu_state', 'vm_memory', 'vm_disk', 'vm_network']


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

    vm = VM.factory('cu-24x7', provider)
    vm.wait_candu_data_available(timeout=1200)

    view = navigate_to(vm, 'candu')
    view.options.interval.fill('Most Recent Hour')

    if graph_type == 'vm_cpu':
        graph = view.vm_cpu
    elif graph_type == 'vm_cpu_state':
        graph = view.vm_cpu_state
    elif graph_type == 'vm_memory':
        graph = view.vm_memory
    elif graph_type == 'vm_disk':
        graph = view.vm_disk
    else:
        graph = view.vm_network

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
