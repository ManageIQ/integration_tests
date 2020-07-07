import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.services.requests import RequestsView
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers', 'setup_provider'),
    pytest.mark.long_running,
    test_requirements.service,
    pytest.mark.tier(3),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE, scope="module"),
]


def test_copy_request_bz1194479(appliance, provider, catalog_item, request):
    """Automate BZ 1194479

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: service
    """
    vm_name = catalog_item.prov_data["catalog"]["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(
            f"{vm_name}0001", provider).cleanup_on_provider()
    )
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    request_description = catalog_item.name
    service_request = appliance.collections.requests.instantiate(request_description,
                                                                 partial_check=True)
    service_request.wait_for_request()
    assert navigate_to(service_request, 'Details')


@pytest.mark.meta(automates=[1749953, 1767660])
@pytest.mark.customer_scenario
def test_services_requester_dropdown_sorting(appliance, generic_catalog_item):
    """
    Bugzilla:
        1749953
        1767660

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/6h
        startsin: 5.11
        testSteps:
            1. Create catalog
            2. Order the catalog items
            3. Go to Services -> Requests
            4. click on the Requester dropdown
        expectedResults:
            1.
            2.
            3.
            4. Requester dropdown should Be Organized alphabetically
    """
    request = ServiceCatalogs(
        appliance, catalog=generic_catalog_item.catalog, name=generic_catalog_item.name
    ).order()
    view = request.create_view(RequestsView)

    all_options = [option.text for option in view.filter_by.requester.all_options]
    assert ["Administrator", "All"] == all_options
