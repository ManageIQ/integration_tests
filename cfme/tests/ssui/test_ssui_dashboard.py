# -*- coding: utf-8 -*-
from datetime import date

import fauxfactory
import pytest

import cfme.intelligence.chargeback.assignments as cb
import cfme.intelligence.chargeback.rates as rates
from cfme.infrastructure.provider import InfraProvider
from cfme.services.dashboard import Dashboard
from cfme import test_requirements
from cfme.utils.log import logger
from cfme.utils import testgen
from cfme.utils.version import current_version
from cfme.utils.appliance import ViaSSUI
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers'),
    test_requirements.ssui,
    pytest.mark.long_running,
    pytest.mark.ignore_stream("upstream", "5.9")
]


pytest_generate_tests = testgen.generate([InfraProvider], required_fields=[
    ['provisioning', 'template'],
    ['provisioning', 'host'],
    ['provisioning', 'datastore']
], scope="module")


@pytest.yield_fixture(scope="module")
def enable_candu(appliance):
    candu = appliance.collections.candus
    server_info = appliance.server.settings
    original_roles = server_info.server_roles_db
    server_info.enable_server_roles(
        'ems_metrics_coordinator', 'ems_metrics_collector', 'ems_metrics_processor')
    candu.enable_all()
    yield
    server_info.update_server_roles_db(original_roles)
    candu.disable_all()


@pytest.yield_fixture(scope="module")
def new_compute_rate(enable_candu):
    # Create a new Compute Chargeback rate
    desc = '{}custom_'.format(fauxfactory.gen_alphanumeric())
    compute = rates.ComputeRate(description=desc, fields={
        'Used CPU': {'per_time': 'Hourly', 'variable_rate': '3'},
        'Allocated CPU Count': {'per_time': 'Hourly', 'fixed_rate': '2'},
        'Used Disk I/O': {'per_time': 'Hourly', 'variable_rate': '2'},
        'Allocated Memory': {'per_time': 'Hourly', 'fixed_rate': '1'},
        'Used Memory': {'per_time': 'Hourly', 'variable_rate': '2'}})
    compute.create()
    storage = rates.StorageRate(description=desc, fields={
        'Used Disk Storage': {'per_time': 'Hourly', 'variable_rate': '3'},
        'Allocated Disk Storage': {'per_time': 'Hourly', 'fixed_rate': '3'}})
    storage.create()
    yield desc
    compute.delete()
    storage.delete()


@pytest.yield_fixture(scope="module")
def assign_chargeback_rate(new_compute_rate):
    # Assign custom Compute rate to the Enterprise and then queue the Chargeback report.
    # description = new_compute_rate
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': new_compute_rate}
        })
    enterprise.computeassign()
    enterprise.storageassign()
    logger.info('Assigning CUSTOM Compute and Storage rates')
    yield
    # Resetting the Chargeback rate assignment
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': '<Nothing>'}
        })
    enterprise.computeassign()
    enterprise.storageassign()


@pytest.fixture(scope="function")
def run_service_chargeback_report(provider, appliance, assign_chargeback_rate,
        order_catalog_item_in_ops_ui):
    catalog_item = order_catalog_item_in_ops_ui
    vmname = '{}0001'.format(catalog_item.provisioning_data['catalog']["vm_name"])

    def verify_records_rollups_table(appliance, provider):
        # Verify that hourly rollups are present in the metric_rollups table
        # before running Service Chargeback report.

        ems = appliance.db.client['ext_management_systems']
        rollups = appliance.db.client['metric_rollups']
        with appliance.db.client.transaction:
            result = (
                appliance.db.client.session.query(rollups.id)
                .join(ems, rollups.parent_ems_id == ems.id)
                .filter(rollups.capture_interval_name == 'hourly', rollups.resource_name == vmname,
                ems.name == provider.name, rollups.timestamp >= date.today())
            )

        for record in appliance.db.client.session.query(rollups).filter(
                rollups.id.in_(result.subquery())):
            # It's okay for these values to be '0'.
            if (record.cpu_usagemhz_rate_average is not None or
               record.cpu_usage_rate_average is not None or
               record.derived_memory_used is not None or
               record.net_usage_rate_average is not None or
               record.disk_usage_rate_average is not None):
                return True

        return False

    wait_for(verify_records_rollups_table, [appliance, provider], timeout=3600,
        message='Waiting for hourly rollups')

    rc, out = appliance.ssh_client.run_rails_command(
        'Service.queue_chargeback_reports')
    assert rc == 0, "Failed to run Service Chargeback report".format(out)


@pytest.mark.parametrize('context', [ViaSSUI])
def test_total_services(appliance, setup_provider, context, order_catalog_item_in_ops_ui):
    """Tests total services count displayed on dashboard."""

    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        assert dashboard.total_services() == dashboard.results()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_current_service(appliance, context):
    """Tests current services count displayed on dashboard."""

    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        assert dashboard.current_services() == dashboard.results()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_retiring_soon(appliance, context):
    """Tests retiring soon(int displayed) service count on dashboard."""

    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        assert dashboard.retiring_soon() == dashboard.results()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_retired_service(appliance, context):
    """Tests count of retired services(int) displayed on dashboard."""

    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        assert dashboard.retired_services() == dashboard.results()


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
@pytest.mark.parametrize('context', [ViaSSUI])
def test_monthly_charges(appliance, setup_provider, context, order_catalog_item_in_ops_ui,
        run_service_chargeback_report):
    """Tests chargeback data"""
    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        monthly_charges = dashboard.monthly_charges()
        logger.info('Monthly charges is {}'.format(monthly_charges))
        assert monthly_charges != '$0'


@pytest.mark.parametrize('context', [ViaSSUI])
def test_total_requests(appliance, context):
    """Tests total requests displayed."""

    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        dashboard.total_requests()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_pending_requests(appliance, context):
    """Tests pending requests displayed on dashboard."""

    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        dashboard.pending_requests()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_approved_requests(appliance, context):
    """Tests approved requests displayed on dashboard."""

    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        dashboard.approved_requests()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_denied_requests(appliance, context):
    """Tests denied requests displayed on dashboard."""

    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        dashboard.denied_requests()
