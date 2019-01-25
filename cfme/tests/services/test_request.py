# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers', 'setup_provider'),
    pytest.mark.long_running,
    test_requirements.service,
    pytest.mark.tier(3),
    pytest.mark.provider([VMwareProvider], scope="module"),
]


def test_copy_request_bz1194479(appliance, provider, catalog_item, request):
    """Automate BZ 1194479

    Polarion:
        assignee: sshveta
        initialEstimate: 1/4h
        casecomponent: Services
    """
    vm_name = catalog_item.prov_data["catalog"]["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(
            "{}0001".format(vm_name), provider).cleanup_on_provider()
    )
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    request_description = catalog_item.name
    service_request = appliance.collections.requests.instantiate(request_description,
                                                                 partial_check=True)
    service_request.wait_for_request()
    assert navigate_to(service_request, 'Details')
