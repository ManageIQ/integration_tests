# -*- coding: utf-8 -*-
from datetime import datetime
from datetime import timedelta

import fauxfactory
import pytest

from cfme.common.candu_views import UtilizationZoomView
from cfme.tests.candu import compare_data_with_unit
from cfme.utils import conf
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.ssh import SSHClient


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
def host(appliance, provider):
    vm = appliance.rest_api.collections.vms.get(name=CANDU_VM)
    vm_host = vm.host.name
    return appliance.collections.hosts.instantiate(name=vm_host)


@pytest.fixture(scope="module")
def temp_appliance_extended_db(temp_appliance_preconfig):
    app = temp_appliance_preconfig
    app.evmserverd.stop()
    app.db.extend_partition()
    app.evmserverd.start()
    return app


@pytest.fixture(scope="module")
def candu_db_restore(temp_appliance_extended_db):
    app = temp_appliance_extended_db
    # get DB backup file
    db_storage_hostname = conf.cfme_data.bottlenecks.hostname
    db_storage_ssh = SSHClient(hostname=db_storage_hostname, **conf.credentials.bottlenecks)
    rand_filename = "/tmp/db.backup_{}".format(fauxfactory.gen_alphanumeric())
    db_storage_ssh.get_file("{}/candu.db.backup".format(
        conf.cfme_data.bottlenecks.backup_path), rand_filename)
    app.ssh_client.put_file(rand_filename, "/tmp/evm_db.backup")

    app.evmserverd.stop()
    app.db.drop()
    app.db.create()
    app.db.restore()
    # When you load a database from an older version of the application, you always need to
    # run migrations.
    # https://bugzilla.redhat.com/show_bug.cgi?id=1643250
    app.db.migrate()
    app.db.fix_auth_key()
    app.db.fix_auth_dbyml()
    app.evmserverd.start()
    app.wait_for_web_ui()


@pytest.mark.parametrize('gp_by', GROUP_BY, ids=['vm_tag'])
@pytest.mark.parametrize('interval', INTERVAL)
@pytest.mark.parametrize('graph_type', HOST_GRAPHS)
def test_tagwise(candu_db_restore, interval, graph_type, gp_by, host):
    """Test Host graphs group by VM tag for hourly and Daily

    prerequisites:
        * C&U enabled appliance
        * C&U data collection enabled for Tag category
        * VM should be taged with proper tag category

    Steps:
        * Capture historical data for host and vm
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

    # wait, for specific vm tag data. It take time to reload metrics with specific vm tag.
    # wait_for(lambda: "London" in graph.all_legends,
    # delay=120, timeout=1500, fail_func=refresh)

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
