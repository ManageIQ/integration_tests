# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.automate.service_dialogs import DialogCollection
from cfme.rest.gen_data import service_catalogs as _service_catalogs
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.services.catalogs.catalog_item import CatalogBundle
from cfme import test_requirements
from selenium.common.exceptions import NoSuchElementException
from cfme.utils import error
from cfme.utils.log import logger


pytestmark = [
    test_requirements.service,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.tier(2)
]


@pytest.yield_fixture(scope="function")
def catalog_item(dialog, catalog):
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type="Generic", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog,
                  dialog=dialog)
    catalog_item.create()
    yield catalog_item


def test_delete_catalog_deletes_service(appliance, dialog, catalog):
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type="Generic", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog,
                  dialog=dialog)
    catalog_item.create()
    catalog.delete()
    service_catalogs = ServiceCatalogs(appliance, catalog, catalog_item.name)
    with error.expected(NoSuchElementException):
        service_catalogs.order()


def test_delete_catalog_item_deletes_service(appliance, catalog_item):
    catalog_item.delete()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    with error.expected(NoSuchElementException):
        service_catalogs.order()


def test_service_circular_reference(catalog_item):
    bundle_name = "first_" + fauxfactory.gen_alphanumeric()
    catalog_bundle = CatalogBundle(name=bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog,
                   catalog_items=[catalog_item.name])
    catalog_bundle.create()
    sec_bundle_name = "sec_" + fauxfactory.gen_alphanumeric()
    sec_catalog_bundle = CatalogBundle(name=sec_bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog,
                   dialog=catalog_item.dialog, catalog_items=[bundle_name])
    sec_catalog_bundle.create()
    with error.expected("Error during 'Resource Add': Adding resource <{}> to Service <{}> "
                        "will create a circular reference".format(sec_bundle_name, bundle_name)):
        catalog_bundle.update({'catalog_items': sec_catalog_bundle.name})


def test_service_generic_catalog_bundle(appliance, catalog_item):
    bundle_name = "generic_" + fauxfactory.gen_alphanumeric()
    catalog_bundle = CatalogBundle(name=bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog,
                   catalog_items=[catalog_item.name])
    catalog_bundle.create()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, bundle_name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', bundle_name)
    request_description = bundle_name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    assert provision_request.is_succeeded()


def test_bundles_in_bundle(appliance, catalog_item):
    bundle_name = "first_" + fauxfactory.gen_alphanumeric()
    catalog_bundle = CatalogBundle(name=bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog,
                   catalog_items=[catalog_item.name])
    catalog_bundle.create()
    sec_bundle_name = "sec_" + fauxfactory.gen_alphanumeric()
    sec_catalog_bundle = CatalogBundle(name=sec_bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog,
                   catalog_items=[bundle_name])
    sec_catalog_bundle.create()
    third_bundle_name = "third_" + fauxfactory.gen_alphanumeric()
    third_catalog_bundle = CatalogBundle(name=third_bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog,
                   catalog_items=[bundle_name, sec_bundle_name])
    third_catalog_bundle.create()
    service_catalogs = ServiceCatalogs(appliance, third_catalog_bundle.catalog, third_bundle_name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', bundle_name)
    request_description = third_bundle_name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    assert provision_request.is_succeeded()


def test_delete_dialog_before_parent_item(appliance, catalog_item):
    service_dialog = DialogCollection(appliance)
    dialog = service_dialog.instantiate(label=catalog_item.dialog.label)
    error_message = ('Dialog \"{}\": Error during delete: Dialog cannot be'
        ' deleted because it is connected to other components.').format(catalog_item.dialog.label)
    with error.expected(error_message):
        dialog.delete()


class TestServiceCatalogViaREST(object):
    @pytest.fixture(scope="function")
    def service_catalogs(self, request, appliance):
        return _service_catalogs(request, appliance.rest_api)

    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_service_catalog(self, appliance, service_catalogs, method):
        """Tests delete service catalog via rest.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == "delete" else 200
        for scl in service_catalogs:
            scl.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == status
            with error.expected("ActiveRecord::RecordNotFound"):
                scl.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == 404

    def test_delete_service_catalogs(self, appliance, service_catalogs):
        """Tests delete service catalogs via rest.

        Metadata:
            test_flag: rest
        """
        appliance.rest_api.collections.service_catalogs.action.delete(*service_catalogs)
        assert appliance.rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            appliance.rest_api.collections.service_catalogs.action.delete(*service_catalogs)
        assert appliance.rest_api.response.status_code == 404

    def test_edit_service_catalog(self, appliance, service_catalogs):
        """Tests editing a service catalog via rest.
        Prerequisities:
            * An appliance with ``/api`` available.
        Steps:
            * POST /api/service_catalogs/<id>/ (method ``edit``) with the ``name``
            * Check if the service_catalog with ``new_name`` exists
        Metadata:
            test_flag: rest
        """
        for ctl in service_catalogs:
            new_name = fauxfactory.gen_alphanumeric()
            response = ctl.action.edit(name=new_name)
            assert appliance.rest_api.response.status_code == 200
            assert response.name == new_name
            ctl.reload()
            assert ctl.name == new_name

    def test_edit_multiple_service_catalogs(self, appliance, service_catalogs):
        """Tests editing multiple service catalogs at time.
        Prerequisities:
            * An appliance with ``/api`` available.
        Steps:
            * POST /api/service_catalogs (method ``edit``)
                with the list of dictionaries used to edit
            * Check if the service_catalogs with ``new_name`` each exist
        Metadata:
            test_flag: rest
        """

        new_names = []
        scls_data_edited = []
        for scl in service_catalogs:
            new_name = fauxfactory.gen_alphanumeric()
            new_names.append(new_name)
            scls_data_edited.append({
                "href": scl.href,
                "name": new_name,
            })
        response = appliance.rest_api.collections.service_catalogs.action.edit(*scls_data_edited)
        assert appliance.rest_api.response.status_code == 200
        assert len(response) == len(new_names)
        for index, resource in enumerate(response):
            assert resource.name == new_names[index]
            scl = service_catalogs[index]
            scl.reload()
            assert scl.name == new_names[index]
