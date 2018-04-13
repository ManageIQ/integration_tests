import pytest

from cfme import test_requirements
from cfme.common.vm import VM
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.c_and_u,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([VMwareProvider],
                         required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')])
]

VM_GRAPHS = ['vm_cpu', 'vm_cpu_state', 'vm_memory', 'vm_disk', 'vm_network']


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
    vm.wait_candu_data_available(timeout=900)

    view = navigate_to(vm, 'candu')
    view.options.interval.fill('Most Recent Hour')

    if graph_type == 'vm_cpu':
        graph = view.vm_cpu
    elif graph_type == 'vm_cpu_state':
        graph = view.vm_cpu_state
    elif graph_type == 'vm_memory':
        graph = view.vm_memory
    else:
        graph = view.vm_network

    assert graph.is_displayed

    for leg in graph.all_legends:
        graph.hide_legends(leg)
        assert not graph.legend_is_displayed(leg)
        graph.display_legends(leg)
        assert graph.legend_is_displayed(leg)

        leg_data = 0
        for data in graph.data_for_legends(leg).values():
            leg_data += float(data[leg].replace(',', '').replace('%', '').split()[0])
        assert leg_data > 0
