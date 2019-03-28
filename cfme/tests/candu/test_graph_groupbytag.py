# -*- coding: utf-8 -*-
from datetime import datetime
from datetime import timedelta

import pytest

from cfme.common.candu_views import UtilizationZoomView
from cfme.tests.candu import compare_data_with_unit
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger


pytestmark = pytest.mark.uncollectif(lambda appliance: appliance.is_pod)

HOST_GRAPHS = ['host_cpu',
               'host_memory',
               'host_disk',
               'host_network',
               'host_cpu_state']

INTERVAL = ['Hourly', 'Daily']

GROUP_BY = ['VM Location']

CANDU_VM = 'cu-24x7'


@pytest.fixture(scope='function')
def host(temp_appliance_extended_db):
    vm = temp_appliance_extended_db.rest_api.collections.vms.get(name=CANDU_VM)

    vm_host = vm.host.name
    return temp_appliance_extended_db.collections.hosts.instantiate(name=vm_host)


@pytest.mark.parametrize('gp_by', GROUP_BY, ids=['vm_tag'])
@pytest.mark.parametrize('interval', INTERVAL)
@pytest.mark.parametrize('graph_type', HOST_GRAPHS)
def test_tagwise(candu_db_restore, interval, graph_type, gp_by, host):
    """Tests for grouping host graphs by VM tag for hourly and Daily intervals

    prerequisites:
        * DB from an appliance on which C&U is enabled
        * DB should have C&U data collection enabled for Tag category
        * DB should have a VM tagged with proper tag category

    Steps:
        * Navigate to Host Utilization Page
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
    """
    view = navigate_to(host, 'candu')
    back_date = datetime.now() - timedelta(days=1)
    data = {'interval': interval, 'group_by': gp_by}

    # Note: If we won't choose backdate then  we have wait for 30min at least for metric collection
    if interval == "Hourly":
        data.update({"calendar": back_date})
    view.options.fill(data)

    # Check graph displayed or not
    try:
        graph = getattr(view.interval_type, graph_type)
    except AttributeError as e:
        logger.error(e)
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
