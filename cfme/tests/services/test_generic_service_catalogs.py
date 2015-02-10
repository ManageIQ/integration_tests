import pytest

from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services.catalogs.catalog_item import CatalogBundle
from cfme.services import requests
from cfme.exceptions import CandidateNotFound
from cfme.web_ui import flash
from utils import error
from utils.randomness import generate_random_string
from utils.log import logger
from utils.wait import wait_for
import utils.randomness as rand


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('logged_in', 'uses_infra_providers'),
    pytest.mark.ignore_stream("5.2")
]


@pytest.yield_fixture(scope="function")
def dialog():
    dialog = "dialog_" + generate_random_string()
    service_dialog = ServiceDialog(label=dialog, description="my dialog", submit=True, cancel=True,
                     tab_label="tab_" + rand.generate_random_string(), tab_desc="my tab desc",
                     box_label="box_" + rand.generate_random_string(), box_desc="my box desc",
                     ele_label="ele_" + rand.generate_random_string(),
                     ele_name=rand.generate_random_string(),
                     ele_desc="my ele desc", choose_type="Text Box",
                     default_text_box="default value")
    service_dialog.create()
    yield dialog


@pytest.yield_fixture(scope="function")
def catalog():
    cat_name = "cat_" + generate_random_string()
    catalog = Catalog(name=cat_name,
                  description="my catalog")
    catalog.create()
    yield catalog


@pytest.yield_fixture(scope="function")
def catalog_item(dialog, catalog):
    item_name = generate_random_string()
    catalog_item = CatalogItem(item_type="Generic", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog.name,
                  dialog=dialog)
    catalog_item.create()
    yield catalog_item


def test_delete_catalog_deletes_service(dialog, catalog):
    item_name = generate_random_string()
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
    bundle_name = "first_" + generate_random_string()
    catalog_bundle = CatalogBundle(name=bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog)
    catalog_bundle.create([catalog_item.name])
    sec_bundle_name = "sec_" + generate_random_string()
    sec_catalog_bundle = CatalogBundle(name=sec_bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog,
                   dialog=catalog_item.dialog)
    sec_catalog_bundle.create([bundle_name])
    with error.expected("Error during 'Resource Add': Adding resource <%s> to Service <%s> "
                        "will create a circular reference" % (sec_bundle_name, bundle_name)):
        catalog_bundle.update({'description': "edit_desc",
                               'cat_item': sec_catalog_bundle.name})


@pytest.mark.meta(blockers=[1144207])
def test_service_generic_catalog_bundle(catalog_item):
    bundle_name = "generic_" + generate_random_string()
    catalog_bundle = CatalogBundle(name=bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog)
    catalog_bundle.create([catalog_item.name])
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_bundle)
    flash.assert_no_errors()
    logger.info('Waiting for cfme provision request for service %s' % bundle_name)
    row_description = 'Provisioning [%s] for Service [%s]' % (bundle_name, bundle_name)
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells],
        fail_func=requests.reload, num_sec=900, delay=20)
    assert row.last_message.text == 'Request complete'


@pytest.mark.meta(blockers=[1144207])
def test_bundles_in_bundle(catalog_item):
    bundle_name = "first_" + generate_random_string()
    catalog_bundle = CatalogBundle(name=bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog)
    catalog_bundle.create([catalog_item.name])
    sec_bundle_name = "sec_" + generate_random_string()
    sec_catalog_bundle = CatalogBundle(name=sec_bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog)
    sec_catalog_bundle.create([bundle_name])
    third_bundle_name = "third_" + generate_random_string()
    third_catalog_bundle = CatalogBundle(name=third_bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog)
    third_catalog_bundle.create([bundle_name, sec_bundle_name])
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, third_catalog_bundle)
    flash.assert_no_errors()
    logger.info('Waiting for cfme provision request for service %s' % bundle_name)
    row_description = 'Provisioning [%s] for Service [%s]' % (third_bundle_name, third_bundle_name)
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells],
        fail_func=requests.reload, num_sec=900, delay=20)
    assert row.last_message.text == 'Request complete'


@pytest.mark.meta(blockers=[1144207])
def test_delete_dialog_before_parent_item(catalog_item):
    service_dialog = ServiceDialog(label=catalog_item.dialog)
    service_dialog.delete()
    flash.assert_message_match(("Dialog \"{}\": Error during 'destroy': Dialog cannot be deleted " +
    "because it is connected to other components.").format(catalog_item.dialog))
