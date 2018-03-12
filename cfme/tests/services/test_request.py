# -*- coding: utf-8 -*-
import pytest

from cfme.common.vm import VM
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.services.service_catalogs import ServiceCatalogs
from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('vm_name', 'uses_infra_providers', 'catalog_item'),
    pytest.mark.long_running,
    test_requirements.service,
    pytest.mark.tier(3),
    pytest.mark.provider([VMwareProvider], scope="module"),
]


def test_copy_request(appliance, setup_provider, provider, catalog_item, request):
    """Automate BZ 1194479"""
    vm_name = catalog_item.provisioning_data["catalog"]["vm_name"]
    request.addfinalizer(lambda: VM.factory(vm_name + "_0001", provider).cleanup_on_provider())
    catalog_item.create()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    request_description = catalog_item.name
    service_request = appliance.collections.requests.instantiate(request_description,
                                                                 partial_check=True)
    service_request.wait_for_request()
    assert navigate_to(service_request, 'Details')
