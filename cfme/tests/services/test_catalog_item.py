# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from cfme.web_ui import flash
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from utils import error
from utils.update import update
from utils.blockers import BZ
import cfme.tests.configure.test_access_control as tac

pytestmark = [pytest.mark.usefixtures("logged_in")]


@pytest.yield_fixture(scope="function")
def dialog():
    dialog = "dialog_" + fauxfactory.gen_alphanumeric()

    element_data = dict(
        ele_label="ele_" + fauxfactory.gen_alphanumeric(),
        ele_name=fauxfactory.gen_alphanumeric(),
        ele_desc="my ele desc",
        choose_type="Text Box",
        default_text_box="default value"
    )

    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                                   submit=True, cancel=True,
                                   tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                                   tab_desc="my tab desc",
                                   box_label="box_" + fauxfactory.gen_alphanumeric(),
                                   box_desc="my box desc")
    service_dialog.create(element_data)
    flash.assert_success_message('Dialog "{}" was added'.format(dialog))
    yield dialog


@pytest.yield_fixture(scope="function")
def catalog():
    catalog = "cat_" + fauxfactory.gen_alphanumeric()
    cat = Catalog(name=catalog,
                  description="my catalog")
    cat.create()
    yield catalog


@pytest.yield_fixture(scope="function")
def catalog_item(dialog, catalog):
    catalog_item = CatalogItem(item_type="Generic",
                               name=fauxfactory.gen_alphanumeric(),
                               description="my catalog", display_in=True,
                               catalog=catalog, dialog=dialog)
    yield catalog_item


def test_create_catalog_item(catalog_item):
    catalog_item.create()
    flash.assert_success_message('Service Catalog Item "{}" was added'.format(catalog_item.name))


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


def test_edit_tags(catalog_item):
    catalog_item.create()
    catalog_item.edit_tags("Cost Center *", "Cost Center 001")


@pytest.mark.meta(blockers=[BZ(1313510, forced_streams=["5.4", "5.5", "upstream"])])
def test_catalog_item_duplicate_name(catalog_item):
    catalog_item.create()
    with error.expected("Name has already been taken"):
        catalog_item.create()


def test_permissions_catalog_item_add(setup_cloud_providers, catalog_item):
    """Test that a catalog can be added only with the right permissions."""
    tac.single_task_permission_test([['Everything', 'Services', 'Catalogs Explorer',
                                      'Catalog Items']],
                                    {'Add Catalog Item': catalog_item.create})
