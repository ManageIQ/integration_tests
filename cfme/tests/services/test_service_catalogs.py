# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.provider import cleanup_vm
from cfme.infrastructure.provider import InfraProvider
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.catalog_item import CatalogBundle
from cfme.services.service_catalogs import ServiceCatalogs
from cfme import test_requirements
from cfme.utils.log import logger
from cfme.utils.wait import wait_for_decorator
from cfme.utils import testgen, error


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('vm_name', 'catalog_item', 'uses_infra_providers'),
    test_requirements.service,
    pytest.mark.long_running
]


pytest_generate_tests = testgen.generate([InfraProvider], required_fields=[
    ['provisioning', 'template'],
    ['provisioning', 'host'],
    ['provisioning', 'datastore']
], scope="module")


@pytest.mark.tier(2)
def test_order_catalog_item(appliance, provider, setup_provider, catalog_item, request,
                            register_event):
    """Tests order catalog item
    Metadata:
        test_flag: provision
    """
    vm_name = catalog_item.provisioning_data['catalog']["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name + "_0001", provider))
    catalog_item.create()

    register_event(target_type='Service', target_name=catalog_item.name,
                   event_type='service_provisioned')

    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info("Waiting for cfme provision request for service {}".format(catalog_item.name))
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    assert provision_request.is_succeeded()


@pytest.mark.tier(2)
def test_order_catalog_item_via_rest(
        request, appliance, provider, setup_provider, catalog_item, catalog):
    """Same as :py:func:`test_order_catalog_item`, but using REST.
    Metadata:
        test_flag: provision, rest
    """
    vm_name = catalog_item.provisioning_data['catalog']["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name, provider))
    catalog_item.create()
    request.addfinalizer(catalog_item.delete)
    catalog = appliance.rest_api.collections.service_catalogs.find_by(name=catalog.name)
    assert len(catalog) == 1
    catalog, = catalog
    template = catalog.service_templates.find_by(name=catalog_item.name)
    assert len(template) == 1
    template, = template
    req = template.action.order()
    assert appliance.rest_api.response.status_code == 200

    @wait_for_decorator(timeout="15m", delay=5)
    def request_finished():
        req.reload()
        logger.info("Request status: {}, Request state: {}, Request message: {}".format(
            req.status, req.request_state, req.message))
        return req.status.lower() == "ok" and req.request_state.lower() == "finished"


@pytest.mark.tier(2)
def test_order_catalog_bundle(appliance, provider, setup_provider, catalog_item, request):
    """Tests ordering a catalog bundle
    Metadata:
        test_flag: provision
    """

    vm_name = catalog_item.provisioning_data['catalog']["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name + "_0001", provider))
    catalog_item.create()
    bundle_name = fauxfactory.gen_alphanumeric()
    catalog_bundle = CatalogBundle(name=bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog,
                   dialog=catalog_item.dialog, catalog_items=[catalog_item.name])
    catalog_bundle.create()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_bundle.name)
    service_catalogs.order()
    logger.info("Waiting for cfme provision request for service {}".format(bundle_name))
    request_description = bundle_name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    assert provision_request.is_succeeded()


# Note here this needs to be reduced, doesn't need to test against all providers
@pytest.mark.usefixtures('has_no_infra_providers')
@pytest.mark.tier(3)
def test_no_template_catalog_item(provider, provisioning, setup_provider, vm_name, dialog, catalog):
    """Tests no template catalog item
    Metadata:
        test_flag: provision
    """
    template, catalog_item_type = map(provisioning.get,
        ('template', 'catalog_item_type'))
    if provider.type == 'rhevm':
        catalog_item_type = "RHEV"
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type=catalog_item_type, name=item_name,
                  description="my catalog", display_in=True, catalog=catalog, dialog=dialog)
    with error.expected("'Catalog/Name' is required"):
        catalog_item.create()


@pytest.mark.tier(3)
def test_edit_catalog_after_deleting_provider(provider, setup_provider, catalog_item):
    """Tests edit catalog item after deleting provider
    Metadata:
        test_flag: provision
    """
    catalog_item.create()
    provider.delete(cancel=False)
    catalog_item.update({'description': 'my edited description'})


@pytest.mark.tier(3)
@pytest.mark.usefixtures('setup_provider')
def test_request_with_orphaned_template(appliance, provider, setup_provider, catalog_item):
    """Tests edit catalog item after deleting provider
    Metadata:
        test_flag: provision
    """
    catalog_item.create()
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
