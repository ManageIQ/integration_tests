import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import providers
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaSSUI
from cfme.utils.blockers import GH
from cfme.utils.providers import ProviderFilter

pytestmark = [
    pytest.mark.meta(server_roles="+automate", blockers=[GH('ManageIQ/integration_tests:7297')]),
    test_requirements.ssui,
    pytest.mark.long_running,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.provider(gen_func=providers,
                         filters=[ProviderFilter(classes=[InfraProvider, CloudProvider],
                                                 required_fields=['provisioning'])])
]


@pytest.mark.rhv2
@pytest.mark.parametrize('context', [ViaSSUI])
def test_service_catalog_crud_ssui(appliance, setup_provider,
                                   context, order_service):
    """Tests Service Catalog in SSUI."""

    catalog_item = order_service
    with appliance.context.use(context):
        if appliance.version >= '5.9':
            dialog_values = {'service_name': "ssui_{}".format(fauxfactory.gen_alphanumeric())}
            service = ServiceCatalogs(appliance, name=catalog_item.name,
                                      dialog_values=dialog_values)
        else:
            service = ServiceCatalogs(appliance, name=catalog_item.name)
        service.add_to_shopping_cart()
        service.order()
