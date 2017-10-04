import pytest

from cfme.infrastructure.provider import InfraProvider
from cfme.services.service_catalogs import ServiceCatalogs
from cfme import test_requirements
from cfme.utils import testgen
from cfme.utils.version import current_version
from cfme.utils.appliance import ViaSSUI


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
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
def test_service_catalog_crud(appliance, setup_provider, context, order_catalog_item_in_ops_ui):
    """Tests Service Catalog in SSUI."""

    service_name = order_catalog_item_in_ops_ui
    with appliance.context.use(context):
        appliance.server.login()
        service = ServiceCatalogs(appliance, name=service_name)
        service.add_to_shopping_cart()
        # TODO - add rest of service catalog tests with various types of services in next phase.
