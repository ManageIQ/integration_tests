# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.common.candu_views import UtilizationZoomView
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
    if entity == 'host':
        vm_host = vm.host.name
        return temp_appliance_extended_db.collections.hosts.instantiate(name=vm_host)
    elif entity == 'cluster':
        provider = temp_appliance_extended_db.rest_api.collections.providers.get(id=vm.ems_id)
        cluster = temp_appliance_extended_db.rest_api.collections.clusters.get(id=vm.ems_cluster_id)
        provider_object = temp_appliance_extended_db.collections.infra_providers.instantiate(
            InfraProvider, name=provider.name)
        return temp_appliance_extended_db.collections.clusters.instantiate(
            name=cluster.name, provider=provider_object)


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

    Bugzillas:
        * 1367560

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

    graph_zoom = ["cluster_host", "cluster_vm"]
    avg_graph = graph_type if graph_type in graph_zoom else "{}_vm_host_avg".format(graph_type)

    # Check graph displayed or not
    try:
        if entity == 'host':
            graph = getattr(view.interval_type, entity + '_' + graph_type)
        elif entity == 'cluster':
            avg_graph = getattr(view, avg_graph)
    except AttributeError:
        pytest.fail('{}_{} graph was not displayed'.format(entity, graph_type))
    assert graph.is_displayed

    graph.zoom_in()
    view = view.browser.create_view(UtilizationZoomView)

    # check for chart and tag London available or not in legend list.
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
