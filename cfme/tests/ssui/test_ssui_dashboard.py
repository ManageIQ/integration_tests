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
    pytest.mark.long_running
]


pytest_generate_tests = testgen.generate([InfraProvider], required_fields=[
    ['provisioning', 'template'],
    ['provisioning', 'host'],
    ['provisioning', 'datastore']
], scope="module")


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
@pytest.mark.parametrize('context', [ViaSSUI])
def test_ssui_dashboard(setup_provider, context, order_catalog_item_in_ops_ui):
    """Tests various Primary and aggregate card values displayed on dashboard."""
    appliance = get_or_create_current_appliance()
    with appliance.context.use(context):
        appliance.server.login()
        dashboard = Dashboard(appliance)
        dashboard.total_service()
        # TODO - add rest of dashboard tests in next phase.
