import pytest

from cfme import test_requirements
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaSSUI
from cfme.utils.blockers import GH

pytestmark = [
    pytest.mark.meta(server_roles="+automate", blockers=[GH('ManageIQ/integration_tests:7297')]),
    test_requirements.ssui,
    pytest.mark.long_running,
    pytest.mark.ignore_stream("upstream")
]


@pytest.mark.parametrize('context', [ViaSSUI])
def test_service_catalog_crud_ui(appliance, context, order_ansible_service_in_ops_ui, request):
    """Tests Ansible Service Catalog in SSUI."""

    service_name = order_ansible_service_in_ops_ui
    with appliance.context.use(context):
        service = ServiceCatalogs(appliance, name=service_name)
        service.add_to_shopping_cart()
        service.order()

        @request.addfinalizer
        def _finalize():
            _service = MyService(appliance, service_name)
            _service.delete()
