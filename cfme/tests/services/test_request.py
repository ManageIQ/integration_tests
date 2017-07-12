# -*- coding: utf-8 -*-
import pytest

from cfme.common.provider import cleanup_vm
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services.requests import Request
from cfme import test_requirements
from utils import testgen
from utils.wait import wait_for

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('vm_name', 'uses_infra_providers', 'catalog_item'),
    pytest.mark.long_running,
    test_requirements.service,
    pytest.mark.tier(3)
]


pytest_generate_tests = testgen.generate([VMwareProvider], scope="module")


def test_copy_request(setup_provider, provider, catalog_item, request):
    """Automate BZ 1194479"""
    vm_name = catalog_item.provisioning_data["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name + "_0001", provider))
    catalog_item.create()
    service_catalogs = ServiceCatalogs(catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    row_description = catalog_item.name
    request_row = Request(row_description, partial_check=True)
    wait_for(request_row.is_finished, fail_func=request_row.reload, num_sec=1800, delay=20)
    request_row.load_details()
