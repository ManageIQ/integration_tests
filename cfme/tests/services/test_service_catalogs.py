import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.markers.env_markers.provider import ONE
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.services.workloads import VmsInstances
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.rest import assert_response
from cfme.utils.wait import wait_for_decorator


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('setup_provider_modscope', 'catalog_item', 'uses_infra_providers'),
    test_requirements.service,
    pytest.mark.long_running,
    pytest.mark.provider([InfraProvider], selector=ONE_PER_TYPE,
                         required_fields=[['provisioning', 'template'],
                                          ['provisioning', 'host'],
                                          ['provisioning', 'datastore']],
                         scope="module"),
]


@pytest.mark.rhv1
@pytest.mark.tier(2)
def test_order_catalog_item(appliance, provider, catalog_item, request,
                            register_event):
    """Tests order catalog item
    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """
    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(
            f"{vm_name}0001", provider).cleanup_on_provider()
    )

    register_event(target_type='Service', target_name=catalog_item.name,
                   event_type='service_provisioned')

    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info(f"Waiting for cfme provision request for service {catalog_item.name}")
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    msg = f"Provisioning failed with the message {provision_request.rest.message}"
    assert provision_request.is_succeeded(), msg


@test_requirements.rest
@pytest.mark.rhv3
@pytest.mark.tier(2)
def test_order_catalog_item_via_rest(
        request, appliance, provider, catalog_item, catalog):
    """Same as :py:func:`test_order_catalog_item`, but using REST.
    Metadata:
        test_flag: provision, rest

    Polarion:
        assignee: pvala
        casecomponent: Services
        caseimportance: high
        initialEstimate: 1/3h
        tags: service
    """
    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(vm_name,
                                                            provider).cleanup_on_provider()
    )
    request.addfinalizer(catalog_item.delete)
    catalog = appliance.rest_api.collections.service_catalogs.find_by(name=catalog.name)
    assert len(catalog) == 1
    catalog, = catalog
    template = catalog.service_templates.find_by(name=catalog_item.name)
    assert len(template) == 1
    template, = template
    req = template.action.order()
    assert_response(appliance)

    @wait_for_decorator(timeout="15m", delay=5)
    def request_finished():
        req.reload()
        logger.info("Request status: {}, Request state: {}, Request message: {}".format(
            req.status, req.request_state, req.message))
        return req.status.lower() == "ok" and req.request_state.lower() == "finished"


@pytest.mark.rhv3
@pytest.mark.tier(2)
def test_order_catalog_bundle(appliance, provider, catalog_item, request):
    """Tests ordering a catalog bundle
    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """

    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(
            f"{vm_name}0001", provider).cleanup_on_provider()
    )
    bundle_name = fauxfactory.gen_alphanumeric(12, start="bundle_")
    catalog_bundle = appliance.collections.catalog_bundles.create(
        bundle_name, description="catalog_bundle",
        display_in=True, catalog=catalog_item.catalog,
        dialog=catalog_item.dialog, catalog_items=[catalog_item.name])
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_bundle.name)
    service_catalogs.order()
    logger.info(f"Waiting for cfme provision request for service {bundle_name}")
    request_description = bundle_name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    msg = f"Provisioning failed with the message {provision_request.rest.message}"
    assert provision_request.is_succeeded(), msg


@pytest.mark.skip('Catalog items are converted to collections. Refactoring is required')
@pytest.mark.rhv3
# Note here this needs to be reduced, doesn't need to test against all providers
@pytest.mark.usefixtures('has_no_infra_providers')
@pytest.mark.tier(3)
def test_no_template_catalog_item(provider, provisioning, dialog, catalog, appliance):
    """Tests no template catalog item
    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/8h
        tags: service
    """
    item_name = fauxfactory.gen_alphanumeric(15, start="cat_item_")
    catalog_item = appliance.collections.catalogs.instantiate(
        # TODO pass catalog class for instantiation
        item_type=provider.catalog_name, name=item_name,
        description="my catalog", display_in=True, catalog=catalog, dialog=dialog)
    with pytest.raises(Exception, match="'Catalog/Name' is required"):
        catalog_item.create()


@pytest.mark.rhv3
@pytest.mark.tier(3)
def test_request_with_orphaned_template(appliance, provider, catalog_item):
    """Tests edit catalog item after deleting provider
    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info(f"Waiting for cfme provision request for service {catalog_item.name}")
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provider.delete()
    provider.wait_for_delete()
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.status.text == 'Error'


@pytest.mark.rhv3
@test_requirements.filtering
@pytest.mark.tier(3)
def test_advanced_search_registry_element(request, appliance):
    """
        Go to Services -> Workloads
        Advanced Search -> Registry element
        Element types select bar shouldn't disappear.

    Polarion:
        assignee: gtalreja
        initialEstimate: 1/4h
        casecomponent: WebUI
    """
    view = navigate_to(VmsInstances(appliance=appliance), 'All')
    view.search.open_advanced_search()
    request.addfinalizer(view.search.close_advanced_search)
    view.search.advanced_search_form.search_exp_editor.registry_form_view.fill({'type': "Registry"})
    assert view.search.advanced_search_form.search_exp_editor.registry_form_view.type.is_displayed


@pytest.mark.tier(2)
@pytest.mark.provider([RHEVMProvider], selector=ONE)
def test_order_service_after_deleting_provider(appliance, provider, setup_provider, catalog_item):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.8
        tags: service
    """
    template_name = catalog_item.prov_data["catalog"]["catalog_name"]["name"]
    template_id = appliance.rest_api.collections.templates.find_by(name=template_name)[0].id

    # delete provider
    provider.delete()
    provider.wait_for_delete()
    assert not provider.exists

    # order catalog item
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    provision_request = service_catalogs.order()
    provision_request.wait_for_request()

    # Verify state and msg
    view = navigate_to(provision_request, "Details")
    assert view.details.request_details.get_text_of("Request State") == "Finished"
    last_msg = f"Error: Source Template/Vm with id [{template_id}] has no EMS, unable to provision"
    assert view.details.request_details.get_text_of("Last Message") == last_msg
