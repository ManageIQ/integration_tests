# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from selenium.common.exceptions import NoSuchElementException

import cfme.tests.configure.test_access_control as tac
from cfme import test_requirements
from cfme.services.catalogs.catalog_item import CatalogItem, CatalogBundle
from cfme.utils import error
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.update import update

pytestmark = [test_requirements.service, pytest.mark.tier(3), pytest.mark.ignore_stream("upstream")]


@pytest.yield_fixture(scope="function")
def catalog_item(dialog, catalog):
    cat_item = CatalogItem(item_type="Generic",
                           name='test_item_' + fauxfactory.gen_alphanumeric(),
                           description="my catalog item", display_in=True,
                           catalog=catalog, dialog=dialog)
    yield cat_item

    # fixture cleanup
    try:
        cat_item.delete()
    except NoSuchElementException:
        logger.warning('test_catalog_item: catalog_item yield fixture cleanup, catalog item "{}" '
                       'not found'.format(cat_item.name))


@pytest.yield_fixture(scope="function")
def catalog_bundle(catalog_item):
    """ Create catalog bundle
        Args:
            catalog_item: as resource for bundle creation
    """
    catalog_item.create()
    bundle_name = "bundle" + fauxfactory.gen_alphanumeric()
    catalog_bundle = CatalogBundle(name=bundle_name, description="catalog_bundle",
                                   display_in=True, catalog=catalog_item.catalog,
                                   dialog=catalog_item.dialog,
                                   catalog_items=[catalog_item.name])
    yield catalog_bundle

    # fixture cleanup
    try:
        catalog_bundle.delete()
    except NoSuchElementException:
        logger.warning('test_catalog_item: catalog_item yield fixture cleanup, catalog item "{}" '
                       'not found'.format(catalog_bundle.name))


@pytest.fixture(scope="function")
def check_catalog_visibility(request, user_restricted, tag):
    def _check_catalog_visibility(test_item_object):
        """
            Args:
                test_item_object: object for visibility check
        """
        test_item_object.create()
        category_name = ' '.join((tag.category.display_name, '*'))
        test_item_object.add_tag(category_name, tag.display_name)
        with user_restricted:
            assert test_item_object.exists
        test_item_object.remove_tag(category_name, tag.display_name)
        with user_restricted:
            assert not test_item_object.exists
    return _check_catalog_visibility


def test_create_catalog_item(catalog_item):
    catalog_item.create()


def test_update_catalog_item(catalog_item):
    catalog_item.create()
    with update(catalog_item):
        catalog_item.description = "my edited item description"


def test_add_button_group(catalog_item):
    catalog_item.create()
    catalog_item.add_button_group()


def test_add_button(catalog_item):
    catalog_item.create()
    catalog_item.add_button()


def test_edit_tags(catalog_item):
    catalog_item.create()
    catalog_item.add_tag("Cost Center *", "Cost Center 001")
    catalog_item.remove_tag("Cost Center *", "Cost Center 001")


@pytest.mark.meta(blockers=[BZ(1313510, forced_streams=["5.7", "5.8", "upstream"])])
def test_catalog_item_duplicate_name(catalog_item):
    catalog_item.create()
    with error.expected("Name has already been taken"):
        catalog_item.create()


@pytest.mark.meta(blockers=[BZ(1460891, forced_streams=["5.7", "5.8", "upstream"])])
def test_permissions_catalog_item_add(catalog_item):
    """Test that a catalog can be added only with the right permissions."""
    tac.single_task_permission_test([['Everything', 'Services', 'Catalogs Explorer',
                                      'Catalog Items']],
                                    {'Add Catalog Item': catalog_item.create})


def test_tagvis_catalog_items(check_catalog_visibility, catalog_item):
    """ Checks catalog item tag visibility for restricted user
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag to catalog item
        2. Login as restricted user, catalog item is visible for user
        3. As admin remove tag
        4. Login as restricted user, catalog item is not visible for user
    """
    check_catalog_visibility(catalog_item)


def test_tagvis_catalog_bundle(check_catalog_visibility, catalog_bundle):
    """ Checks catalog bundle tag visibility for restricted user
        Prerequisites:
            Catalog, tag, role, group, catalog item and restricted user should be created

        Steps:
            1. As admin add tag to catalog bundle
            2. Login as restricted user, catalog bundle is visible for user
            3. As admin remove tag
            4. Login as restricted user, catalog bundle is not visible for user
        """
    check_catalog_visibility(catalog_bundle)
