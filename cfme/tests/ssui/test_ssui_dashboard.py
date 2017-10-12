# -*- coding: utf-8 -*-
import cfme.intelligence.chargeback.rates as rates
import cfme.intelligence.chargeback.assignments as cb
import fauxfactory
import pytest

from cfme.infrastructure.provider import InfraProvider
from cfme.services.dashboard import Dashboard
from cfme import test_requirements

from cfme.utils import testgen
from cfme.utils.version import current_version
from cfme.utils.appliance import ViaSSUI

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers'),
    test_requirements.ssui,
    pytest.mark.long_running,
    pytest.mark.uncollectif(lambda: current_version() < '5.8'),
    pytest.mark.ignore_stream("upstream")
]


pytest_generate_tests = testgen.generate([InfraProvider], required_fields=[
    ['provisioning', 'template'],
    ['provisioning', 'host'],
    ['provisioning', 'datastore']
], scope="module")


@pytest.yield_fixture(scope="module")
def new_compute_rate():
    # Create a new Compute Chargeback rate
    try:
        desc = 'custom_' + fauxfactory.gen_alphanumeric()
        compute = rates.ComputeRate(description=desc,
                    fields={'Used CPU':
                            {'per_time': 'Hourly', 'variable_rate': '3'},
                            'Allocated CPU Count':
                            {'per_time': 'Hourly', 'fixed_rate': '2'},
                            'Used Disk I/O':
                            {'per_time': 'Hourly', 'variable_rate': '2'},
                            'Allocated Memory':
                            {'per_time': 'Hourly', 'fixed_rate': '1'},
                            'Used Memory':
                            {'per_time': 'Hourly', 'variable_rate': '2'}})
        compute.create()
        storage = rates.StorageRate(description=desc,
                    fields={'Used Disk Storage':
                            {'per_time': 'Hourly', 'variable_rate': '3'},
                            'Allocated Disk Storage':
                            {'per_time': 'Hourly', 'fixed_rate': '3'}})
        storage.create()
        yield desc
    finally:
        compute.delete()
        storage.delete()


@pytest.yield_fixture(scope="module")
def assign_chargeback_rate(new_compute_rate):
    # Assign custom Compute rate to the Enterprise and then queue the Chargeback report.
    description = new_compute_rate
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': description}
        })
    enterprise.computeassign()
    enterprise.storageassign()

    yield

    # Resetting the Chargeback rate assignment
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': '<Nothing>'}
        })
    enterprise.computeassign()
    enterprise.storageassign()


@pytest.fixture(scope="module")
def run_service_chargeback_report(provider, appliance, assign_chargeback_rate):
    rc, out = appliance.ssh_client.run_rails_command(
        'Service.queue_chargeback_reports')
    assert rc == 0, "Failed to run Service Chargeback report".format(out)


@pytest.mark.parametrize('context', [ViaSSUI])
def test_total_services(appliance, setup_provider, context, order_catalog_item_in_ops_ui):
    """Tests total services displayed on dashboard."""

    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        assert dashboard.total_services() == dashboard.num_of_rows()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_current_service(appliance, context):
    """Tests current services displayed on dashboard."""

    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        assert dashboard.current_services() == dashboard.num_of_rows()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_retiring_soon(appliance, context):
    """Tests retiring soon services displayed on dashboard."""

    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        assert dashboard.retiring_soon() == dashboard.num_of_rows()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_retired_service(appliance, context):
    """Tests retired services displayed on dashboard."""

    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        assert dashboard.retired_services() == dashboard.num_of_rows()


@pytest.mark.parametrize('context', [ViaSSUI])
def test_monthly_charges(appliance, setup_provider, context, order_catalog_item_in_ops_ui,
        run_service_chargeback_report):
    """Tests chargeback data"""

    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        monthly_charges = dashboard.monthly_charges()
        assert monthly_charges > 0


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
