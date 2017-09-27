# -*- coding: utf-8 -*-

import pytest

from cfme.infrastructure.provider import InfraProvider
from cfme.services.dashboard import Dashboard
from cfme import test_requirements

from cfme.utils import testgen
from cfme.utils.version import current_version
from cfme.utils.appliance import get_or_create_current_appliance, ViaSSUI

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
def test_monthly_charges(appliance, context):
    """Tests chargeback data"""

    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        dashboard.monthly_charges()


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
