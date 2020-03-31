import pytest

from cfme import test_requirements
from cfme.common.candu_views import UtilizationZoomView
from cfme.infrastructure.provider import InfraProvider
from cfme.tests.candu import compare_data_with_unit
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.c_and_u
]

GRAPHS = ['cpu',
          'memory',
          'disk',
          'network',
          'cpu_state']

INTERVAL = ['Hourly', 'Daily']

GROUP_BY = ['VM Location']

CANDU_VM = 'cu-24x7'

ENTITY = ['host', 'cluster']


@pytest.fixture(scope='function')
def entity_object(temp_appliance_extended_db, entity):
    vm = temp_appliance_extended_db.rest_api.collections.vms.get(name=CANDU_VM)
    provider = temp_appliance_extended_db.rest_api.collections.providers.get(id=vm.ems_id)
    provider_object = temp_appliance_extended_db.collections.infra_providers.instantiate(
        InfraProvider, name=provider.name)
    vm_object = temp_appliance_extended_db.collections.infra_vms.instantiate(
        CANDU_VM, provider_object)
    if entity == 'host':
        return vm_object.host
    elif entity == 'cluster':
        return vm_object.cluster
    """
    if entity == 'host':
        vm_host = vm.host.name
        return temp_appliance_extended_db.collections.hosts.instantiate(name=vm_host)
    elif entity == 'cluster':
        provider = temp_appliance_extended_db.rest_api.collections.providers.get(id=vm.ems_id)
        provider_object = temp_appliance_extended_db.collections.infra_providers.instantiate(
            InfraProvider, name=provider.name)
        vm_object = temp_appliance_extended_db.collections.infra_vms.instantiate(
            CANDU_VM, provider_object)
        return vm_object.cluster
    """


@pytest.mark.parametrize('gp_by', GROUP_BY, ids=['vm_tag'])
@pytest.mark.parametrize('interval', INTERVAL)
@pytest.mark.parametrize('graph_type', GRAPHS)
@pytest.mark.parametrize('entity', ENTITY)
def test_tagwise(candu_db_restore, interval, graph_type, gp_by, entity, entity_object):
    """Tests for grouping host graphs by VM tag for hourly and Daily intervals

    prerequisites:
        * DB from an appliance on which C&U is enabled
        * DB should have C&U data collection enabled for Tag category
        * DB should have a VM and VM/host tagged with proper tag category

    Steps:
        * Navigate to Host/Cluster Utilization Page
        * Select interval(Hourly or Daily)
        * Select group by option with VM tag
        * Check graph displayed or not
        * Zoom graph to get Table
        * Check tag assigned to VM available in chart legends
        * Compare table and graph data

    Bugzilla:
        1367560

    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    if entity == 'host':
        view = navigate_to(entity_object, 'candu')
    elif entity == 'cluster':
        view = navigate_to(entity_object, 'Utilization')
    data = {'interval': interval, 'group_by': gp_by}
    view.options.fill(data)

    entity_graph = '{}_{}'.format(entity, graph_type)

    # Check graph displayed or not
    try:
        if entity == 'host':
            graph = getattr(view.interval_type, entity_graph)
        elif entity == 'cluster':
            graph = getattr(view, entity_graph)
    except AttributeError:
        pytest.fail('{} graph was not displayed'.format(entity_graph))
    assert graph.is_displayed

    # zoom in button not available with normal graph except Host and VM.
    # We have to use vm or host average graph for zoom in operation.
    if entity == 'cluster':
        graph_zoom = ["cluster_host", "cluster_vm"]
        enity_avg_graph = '{}_vm_host_avg'.format(entity_graph)
        # entity_graph = entity + '_' + graph_type
        avg_graph = entity_graph if entity_graph in graph_zoom else enity_avg_graph
        try:
            avg_graph = getattr(view, avg_graph)
        except AttributeError:
            pytest.fail('{} graph was not displayed'.format(entity_graph))

    graph.zoom_in()
    view = view.browser.create_view(UtilizationZoomView)

    # check for chart and tag London available or not in legend list.
    # wait, some time graph take time to load
    view.flush_widget_cache()
    assert view.chart.is_displayed
    legends = view.chart.all_legends
    assert "London" in legends

    # compare graph and table data
    graph_data = view.chart.all_data
    # Clear cache of table widget before read else it will mismatch headers.
    view.table.clear_cache()
    table_data = view.table.read()
    compare_data_with_unit(table_data=table_data, graph_data=graph_data, legends=legends)
