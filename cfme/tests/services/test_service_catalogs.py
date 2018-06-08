# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.services.catalogs.catalog_items import EditCatalogItemView
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.services.workloads import VmsInstances
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.rest import assert_response
from cfme.utils.wait import wait_for_decorator


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('setup_provider', 'catalog_item', 'uses_infra_providers'),
    test_requirements.service,
    pytest.mark.long_running,
    pytest.mark.provider([InfraProvider],
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
    """
    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(
            "{}0001".format(vm_name), provider).delete_from_provider()
    )

    register_event(target_type='Service', target_name=catalog_item.name,
                   event_type='service_provisioned')

    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info("Waiting for cfme provision request for service {}".format(catalog_item.name))
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    msg = "Provisioning failed with the message {}".format(provision_request.rest.message)
    assert provision_request.is_succeeded(), msg


@pytest.mark.rhv3
@pytest.mark.tier(2)
def test_order_catalog_item_via_rest(
        request, appliance, provider, catalog_item, catalog):
    """Same as :py:func:`test_order_catalog_item`, but using REST.
    Metadata:
        test_flag: provision, rest
    """
    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(vm_name,
                                                            provider).delete_from_provider()
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
    """

    vm_name = catalog_item.prov_data['catalog']["vm_name"]
    request.addfinalizer(
        lambda: appliance.collections.infra_vms.instantiate(
            "{}0001".format(vm_name), provider).delete_from_provider()
    )
    bundle_name = fauxfactory.gen_alphanumeric()
    catalog_bundle = appliance.collections.catalog_bundles.create(
        bundle_name, description="catalog_bundle",
        display_in=True, catalog=catalog_item.catalog,
        dialog=catalog_item.dialog, catalog_items=[catalog_item.name])
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_bundle.name)
    service_catalogs.order()
    logger.info("Waiting for cfme provision request for service {}".format(bundle_name))
    request_description = bundle_name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    msg = "Provisioning failed with the message {}".format(provision_request.rest.message)
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
    """
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = appliance.collections.catalogs.instantiate(
        # TODO pass catalog class for instantiation
        item_type=provider.catalog_name, name=item_name,
        description="my catalog", display_in=True, catalog=catalog, dialog=dialog)
    with pytest.raises(Exception, match="'Catalog/Name' is required"):
        catalog_item.create()


@pytest.mark.rhv3
@pytest.mark.tier(3)
def test_edit_catalog_after_deleting_provider(provider, catalog_item):
    """Tests edit catalog item after deleting provider
    Metadata:
        test_flag: provision
    """
    provider.delete(cancel=False)
    changes = {'basic_info.description': 'my edited description'}
    if provider.appliance.version > '5.9.0.20' and provider.one_of(RHEVMProvider):
        with pytest.raises(AssertionError):
            catalog_item.update(changes)
        view = provider.create_view(EditCatalogItemView)
        view.flash.assert_message("'Environment/Cluster Name' is required", t='error')
        view.flash.assert_message("'Network/Virtual NIC Profile ID' is required", t='error')
    else:
        catalog_item.update(changes)


@pytest.mark.rhv3
@pytest.mark.tier(3)
def test_request_with_orphaned_template(appliance, provider, catalog_item):
    """Tests edit catalog item after deleting provider
    Metadata:
        test_flag: provision
    """
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info("Waiting for cfme provision request for service {}".format(catalog_item.name))
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provider.delete(cancel=False)
    provider.wait_for_delete()
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.status.text == 'Error'


@pytest.mark.rhv3
@pytest.mark.tier(3)
def test_advanced_search_registry_element(request, appliance):
    """
        Go to Services -> Workloads
        Advanced Search -> Registry element
        Element types select bar shouldn't disappear.
    """
    view = navigate_to(VmsInstances(appliance=appliance), 'All')
    view.search.open_advanced_search()
    request.addfinalizer(view.search.close_advanced_search)
    view.search.advanced_search_form.search_exp_editor.registry_form_view.fill({'type': "Registry"})
    assert view.search.advanced_search_form.search_exp_editor.registry_form_view.type.is_displayed
