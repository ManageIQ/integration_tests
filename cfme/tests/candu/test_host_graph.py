import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.c_and_u,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([VMwareProvider, RHEVMProvider],
                         required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')])
]


HOST_RECENT_HR_GRAPHS = ['host_cpu',
                         'host_memory',
                         'host_disk',
                         'host_network']


@pytest.fixture(scope='function')
def host(appliance, provider):
    collection = appliance.collections.hosts
    for test_host in provider.data['hosts']:
        if not test_host.get('test_fleece', False):
            continue
        return collection.instantiate(name=test_host.name, provider=provider)


@pytest.mark.uncollectif(lambda provider, graph_type:
                         provider.one_of(RHEVMProvider) and
                         graph_type == "host_disk")
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
        assignee: None
        initialEstimate: None
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
