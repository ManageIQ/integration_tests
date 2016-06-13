# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.automate.service_dialogs import ServiceDialog
from cfme.rest import service_catalogs as _service_catalogs
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services.catalogs.catalog_item import CatalogBundle
from cfme.services import requests
from cfme.exceptions import CandidateNotFound
from cfme.web_ui import flash
from utils import error
from utils.log import logger
from utils.wait import wait_for

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('logged_in', 'uses_infra_providers'),
    pytest.mark.tier(2)
]


@pytest.yield_fixture(scope="function")
def catalog_item(dialog, catalog):
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type="Generic", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog.name,
                  dialog=dialog)
    catalog_item.create()
    yield catalog_item


def test_delete_catalog_deletes_service(dialog, catalog):
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type="Generic", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog.name,
                  dialog=dialog)
    catalog_item.create()
    catalog.delete()
    service_catalogs = ServiceCatalogs("service_name")
    with error.expected(CandidateNotFound):
        service_catalogs.order(catalog.name, catalog_item)


def test_delete_catalog_item_deletes_service(catalog_item):
    catalog_item.delete()
    service_catalogs = ServiceCatalogs("service_name")
    with error.expected(CandidateNotFound):
        service_catalogs.order(catalog_item.catalog, catalog_item)


def test_service_circular_reference(catalog_item):
    bundle_name = "first_" + fauxfactory.gen_alphanumeric()
    catalog_bundle = CatalogBundle(name=bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog)
    catalog_bundle.create([catalog_item.name])
    sec_bundle_name = "sec_" + fauxfactory.gen_alphanumeric()
    sec_catalog_bundle = CatalogBundle(name=sec_bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog,
                   dialog=catalog_item.dialog)
    sec_catalog_bundle.create([bundle_name])
    with error.expected("Error during 'Resource Add': Adding resource <{}> to Service <{}> "
                        "will create a circular reference".format(sec_bundle_name, bundle_name)):
        catalog_bundle.update({'description': "edit_desc",
                               'cat_item': sec_catalog_bundle.name})


def test_service_generic_catalog_bundle(catalog_item):
    bundle_name = "generic_" + fauxfactory.gen_alphanumeric()
    catalog_bundle = CatalogBundle(name=bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog)
    catalog_bundle.create([catalog_item.name])
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_bundle)
    flash.assert_no_errors()
    logger.info('Waiting for cfme provision request for service %s', bundle_name)
    row_description = bundle_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=900, delay=20)
    assert row.last_message.text == 'Request complete'


def test_bundles_in_bundle(catalog_item):
    bundle_name = "first_" + fauxfactory.gen_alphanumeric()
    catalog_bundle = CatalogBundle(name=bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog)
    catalog_bundle.create([catalog_item.name])
    sec_bundle_name = "sec_" + fauxfactory.gen_alphanumeric()
    sec_catalog_bundle = CatalogBundle(name=sec_bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog)
    sec_catalog_bundle.create([bundle_name])
    third_bundle_name = "third_" + fauxfactory.gen_alphanumeric()
    third_catalog_bundle = CatalogBundle(name=third_bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog)
    third_catalog_bundle.create([bundle_name, sec_bundle_name])
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, third_catalog_bundle)
    flash.assert_no_errors()
    logger.info('Waiting for cfme provision request for service %s', bundle_name)
    row_description = third_bundle_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=900, delay=20)
    assert row.last_message.text == 'Request complete'


@pytest.mark.meta(blockers=['GH#ManageIQ/manageiq:7277'])
def test_delete_dialog_before_parent_item(catalog_item):
    service_dialog = ServiceDialog(label=catalog_item.dialog)
    service_dialog.delete()
    flash.assert_message_match(("Dialog \"{}\": Error during 'destroy': Dialog cannot be deleted " +
    "because it is connected to other components.").format(catalog_item.dialog))


class TestServiceCatalogViaREST(object):
    @pytest.fixture(scope="function")
    def service_catalogs(self, request, rest_api):
        return _service_catalogs(request, rest_api)

    def test_delete_service_catalog(self, rest_api, service_catalogs):
        """Tests delete service catalog via rest

        Metadata:
            test_flag: rest
        """
        scl = service_catalogs[0]
        scl.action.delete()
        with error.expected("ActiveRecord::RecordNotFound"):
            scl.action.delete()

    def test_delete_service_catalogs(self, rest_api, service_catalogs):
        """Tests delete service catalogs via rest

        Metadata:
            test_flag: rest
        """
        rest_api.collections.service_catalogs.action.delete(*service_catalogs)
        with error.expected("ActiveRecord::RecordNotFound"):
            rest_api.collections.service_catalogs.action.delete(*service_catalogs)

    def test_edit_service_catalog(self, rest_api, service_catalogs):
        """Tests editing a service catalog via rest.
        Prerequisities:
            * An appliance with ``/api`` available.
        Steps:
            * POST /api/service_catalogs/<id>/ (method ``edit``) with the ``name``
            * Check if the service_catalog with ``new_name`` exists
        Metadata:
            test_flag: rest
        """
        ctl = service_catalogs[0]
        new_name = fauxfactory.gen_alphanumeric()
        ctl.action.edit(name=new_name)
        wait_for(
            lambda: rest_api.collections.service_catalogs.find_by(name=new_name),
            num_sec=180,
            delay=10,
        )

    def test_edit_multiple_service_catalogs(self, rest_api, service_catalogs):
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
        rest_api.collections.service_catalogs.action.edit(*scls_data_edited)
        for new_name in new_names:
            wait_for(
                lambda: rest_api.collections.service_catalogs.find_by(name=new_name),
                num_sec=180,
                delay=10,
            )
