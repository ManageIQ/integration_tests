import pytest
from cfme.web_ui import flash
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from utils.randomness import generate_random_string
from utils import error
from utils.update import update


pytestmark = [pytest.mark.usefixtures("logged_in")]


@pytest.yield_fixture(scope="function")
def dialog():
    dialog = "dialog_" + generate_random_string()
    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                                   submit=True, cancel=True)
    service_dialog.create()
    flash.assert_success_message('Dialog "%s" was added' % dialog)
    yield dialog


@pytest.yield_fixture(scope="function")
def catalog():
    catalog = "cat_" + generate_random_string()
    cat = Catalog(name=catalog,
                  description="my catalog")
    cat.create()
    yield catalog


@pytest.yield_fixture(scope="function")
def catalog_item(dialog, catalog):
    catalog_item = CatalogItem(item_type="Generic",
                               name=generate_random_string(),
                               description="my catalog", display_in=True,
                               catalog=catalog, dialog=dialog)
    yield catalog_item


def test_create_catalog_item(catalog_item):
    catalog_item.create()


def test_update_catalog_item(catalog_item):
    catalog_item.create()
    with update(catalog_item):
        catalog_item.description = "my edited description"


def test_delete_catalog_item(catalog_item):
    catalog_item.create()
    catalog_item.delete()


def test_add_button_group(catalog_item):
    catalog_item.create()
    catalog_item.add_button_group()


def test_add_button(catalog_item):
    catalog_item.create()
    catalog_item.add_button()


@pytest.mark.xfail(message='downstream - https://bugzilla.redhat.com/show_bug.cgi?id=996789 ;'
                           'upstream -  https://bugzilla.redhat.com/show_bug.cgi?id=1092651')
def test_catalog_item_duplicate_name(catalog_item):
    catalog_item.create()
    with error.expected("Name has already been taken"):
        catalog_item.create()
