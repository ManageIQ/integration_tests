# -*- coding: utf-8 -*-
from datetime import date, timedelta

import fauxfactory
import pytest

import cfme.intelligence.chargeback.assignments as cb
import cfme.intelligence.chargeback.rates as rates
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.services.dashboard import Dashboard
from cfme import test_requirements
from cfme.utils.appliance import ViaSSUI
from cfme.utils.blockers import GH
from cfme.utils.log import logger
from cfme.utils.version import current_version
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.meta(server_roles="+automate", blockers=[GH('ManageIQ/integration_tests:7297')]),
    pytest.mark.usefixtures('uses_infra_providers'),
    test_requirements.ssui,
    pytest.mark.long_running,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.provider([InfraProvider],
                         required_fields=[['provisioning', 'template'],
                                          ['provisioning', 'host'],
                                          ['provisioning', 'datastore']],
                         scope="module"),
]


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def assign_chargeback_rate(new_compute_rate):
    """Assign custom Compute rate to the Enterprise and then queue the Chargeback report."""
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


def verify_vm_uptime(appliance, provider, vmname):
    """Verifies VM uptime is at least one hour.

    One hour is the shortest duration for which VMs can be charged.
    """
    vm_creation_time = appliance.rest_api.collections.vms.get(name=vmname).created_on
    return appliance.utc_time() - vm_creation_time > timedelta(hours=1)


@pytest.fixture(scope="function")
def run_service_chargeback_report(provider, appliance, assign_chargeback_rate,
                                  order_service):
    catalog_item = order_service
    vmname = '{}0001'.format(catalog_item.prov_data['catalog']["vm_name"])

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

    if provider.one_of(SCVMMProvider):
        wait_for(verify_vm_uptime, [appliance, provider, vmname], timeout=3610,
           delay=10, message='Waiting for VM to be up for at least one hour')
    else:
        wait_for(verify_records_rollups_table, [appliance, provider], timeout=3600,
            delay=10, message='Waiting for hourly rollups')

    result = appliance.ssh_client.run_rails_command(
        'Service.queue_chargeback_reports')
    assert result.success, "Failed to run Service Chargeback report".format(result.output)


@pytest.mark.rhv3
@pytest.mark.parametrize('context', [ViaSSUI])
def test_total_services(appliance, setup_provider, context, order_service):
    """Tests total services count displayed on dashboard."""

    with appliance.context.use(context):
        dashboard = Dashboard(appliance)
        assert dashboard.total_services() == dashboard.results()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_current_service(appliance, context):
    """Tests current services count displayed on dashboard."""

    with appliance.context.use(context):
        dashboard = Dashboard(appliance)
        assert dashboard.current_services() == dashboard.results()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_retiring_soon(appliance, context):
    """Tests retiring soon(int displayed) service count on dashboard."""

    with appliance.context.use(context):
        dashboard = Dashboard(appliance)
        assert dashboard.retiring_soon() == dashboard.results()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_retired_service(appliance, context):
    """Tests count of retired services(int) displayed on dashboard."""

    with appliance.context.use(context):
        dashboard = Dashboard(appliance)
        assert dashboard.retired_services() == dashboard.results()


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
@pytest.mark.parametrize('context', [ViaSSUI])
def test_monthly_charges(appliance, has_no_providers_modscope, setup_provider, context,
        order_service, run_service_chargeback_report):
    """Tests chargeback data"""
    with appliance.context.use(context):
        dashboard = Dashboard(appliance)
        monthly_charges = dashboard.monthly_charges()
        logger.info('Monthly charges is {}'.format(monthly_charges))
        assert monthly_charges != '$0'


@pytest.mark.parametrize('context', [ViaSSUI])
def test_total_requests(appliance, context):
    """Tests total requests displayed."""

    with appliance.context.use(context):
        dashboard = Dashboard(appliance)
        dashboard.total_requests()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_pending_requests(appliance, context):
    """Tests pending requests displayed on dashboard."""

    with appliance.context.use(context):
        dashboard = Dashboard(appliance)
        dashboard.pending_requests()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_approved_requests(appliance, context):
    """Tests approved requests displayed on dashboard."""

    with appliance.context.use(context):
        dashboard = Dashboard(appliance)
        dashboard.approved_requests()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_denied_requests(appliance, context):
    """Tests denied requests displayed on dashboard."""

    with appliance.context.use(context):
        dashboard = Dashboard(appliance)
        dashboard.denied_requests()
