import pytest

from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services.catalogs.catalog_item import CatalogBundle
from cfme.exceptions import CandidateNotFound
from utils import error
from utils.randomness import generate_random_string


pytestmark = [
    pytest.mark.usefixtures("logged_in"),
    pytest.mark.fixtureconf(server_roles="+automate"),
    pytest.mark.usefixtures('server_roles', 'uses_infra_providers')
]


@pytest.yield_fixture(scope="function")
def dialog():
    dialog = "dialog_" + generate_random_string()
    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                     submit=True, cancel=True)
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
    bundle_name = "first_"+generate_random_string()
    catalog_bundle = CatalogBundle(name=bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog,
                   dialog=catalog_item.dialog, cat_item=catalog_item.name)
    catalog_bundle.create()
    sec_bundle_name = "sec_"+generate_random_string()
    sec_catalog_bundle = CatalogBundle(name=sec_bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog,
                   dialog=catalog_item.dialog, cat_item=bundle_name)
    sec_catalog_bundle.create()
    with error.expected("Error during 'Resource Add': Adding resource <%s> to "
        "Service <%s> will create a circular reference" % (sec_bundle_name,bundle_name)):
        catalog_bundle.update({'description': "edit_desc",
                               'cat_item': sec_catalog_bundle.name})
