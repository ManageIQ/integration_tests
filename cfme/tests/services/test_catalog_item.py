# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from selenium.common.exceptions import NoSuchElementException

import cfme.tests.configure.test_access_control as tac
from cfme import test_requirements
from cfme.services.catalogs.catalog_items import AllCatalogItemView, AddCatalogItemView
from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.update import update

pytestmark = [test_requirements.service, pytest.mark.tier(3), pytest.mark.ignore_stream("upstream")]


@pytest.fixture(scope="function")
def catalog_item(appliance, dialog, catalog):
    cat_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name='test_item_{}'.format(fauxfactory.gen_alphanumeric()),
        description="my catalog item", display_in=True,
        catalog=catalog, dialog=dialog
    )
    view = cat_item.create_view(AllCatalogItemView)
    assert view.is_displayed
    view.flash.assert_success_message('Service Catalog Item "{}" was added'.format(
        cat_item.name))
    yield cat_item

    # fixture cleanup
    try:
        cat_item.delete()
    except NoSuchElementException:
        logger.warning('test_catalog_item: catalog_item yield fixture cleanup, catalog item "{}" '
                       'not found'.format(cat_item.name))


@pytest.fixture(scope="function")
def catalog_bundle(appliance, catalog_item):
    """ Create catalog bundle
        Args:
            catalog_item: as resource for bundle creation
    """
    bundle_name = "bundle" + fauxfactory.gen_alphanumeric()
    catalog_bundle = appliance.collections.catalog_bundles.create(
        bundle_name, description="catalog_bundle",
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
def check_catalog_visibility(user_restricted, tag):
    def _check_catalog_visibility(test_item_object):
        """
            Args:
                test_item_object: object for visibility check
        """
        test_item_object.add_tag(tag)
        with user_restricted:
            assert test_item_object.exists
        test_item_object.remove_tag(tag)
        with user_restricted:
            assert not test_item_object.exists
    return _check_catalog_visibility


def test_catalog_item_crud(appliance, dialog, catalog):
    """
    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: high
        initialEstimate: 1/8h
    """
    cat_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name="test_item_{}".format(fauxfactory.gen_alphanumeric()),
        description="my catalog item",
        display_in=True,
        catalog=catalog,
        dialog=dialog
    )
    view = cat_item.create_view(AllCatalogItemView)
    assert view.is_displayed
    view.flash.assert_success_message('Service Catalog Item "{}" was added'.format(cat_item.name))
    assert cat_item.exists
    with update(cat_item):
        cat_item.description = "my edited description"
    assert cat_item.description == "my edited description"
    cat_item.delete()
    view.flash.assert_message("The selected Catalog Item was deleted")
    assert not cat_item.exists


def test_add_button_group(catalog_item, appliance):
    """
    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
    """
    button_name = catalog_item.add_button_group()
    view = appliance.browser.create_view(BaseLoggedInPage)
    if appliance.version.is_in_series('5.8'):
        message = 'Buttons Group "{}" was added'.format(button_name)
    else:
        message = 'Button Group "{}" was added'.format(button_name)
    view.flash.assert_success_message(message)


def test_add_button(catalog_item, appliance):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    button_name = catalog_item.add_button()
    view = appliance.browser.create_view(BaseLoggedInPage)
    if appliance.version.is_in_series('5.8'):
        message = 'Button "{}" was added'.format(button_name)
    else:
        message = 'Custom Button "{}" was added'.format(button_name)
    view.flash.assert_success_message(message)


def test_edit_tags(catalog_item):
    """
    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/8h
    """
    tag = catalog_item.add_tag()
    catalog_item.remove_tag(tag)


@pytest.mark.meta(blockers=[BZ(1531512, forced_streams=["5.9", "5.10", "upstream"])])
def test_catalog_item_duplicate_name(appliance, dialog, catalog):
    """
    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
    """
    cat_item_name = fauxfactory.gen_alphanumeric()
    cat_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name=cat_item_name,
        description="my catalog item",
        display_in=True,
        catalog=catalog,
        dialog=dialog
    )
    view = cat_item.create_view(AllCatalogItemView)
    view.wait_displayed()
    view.flash.assert_success_message('Service Catalog Item "{}" was added'.format(cat_item.name))
    with pytest.raises(AssertionError):
        appliance.collections.catalog_items.create(
            appliance.collections.catalog_items.GENERIC,
            name=cat_item_name,
            description="my catalog item",
            display_in=True,
            catalog=catalog,
            dialog=dialog
        )
    view = cat_item.create_view(AddCatalogItemView)
    view.wait_displayed()
    view.flash.assert_message('Name has already been taken')


def test_permissions_catalog_item_add(appliance, catalog, dialog, request):
    """Test that a catalog can be added only with the right permissions.

    Polarion:
        assignee: nansari
        casecomponent: services
        caseimportance: high
        initialEstimate: 1/8h
    """

    def _create_catalog(appliance):
        cat_item = appliance.collections.catalog_items.create(
            appliance.collections.catalog_items.GENERIC,
            name='test_item_{}'.format(fauxfactory.gen_alphanumeric()),
            description="my catalog item",
            display_in=True,
            catalog=catalog,
            dialog=dialog
        )
        request.addfinalizer(lambda: cat_item.delete())
    test_product_features = [['Everything', 'Services', 'Catalogs Explorer', 'Catalog Items']]
    test_actions = {'Add Catalog Item': _create_catalog}
    tac.single_task_permission_test(appliance, test_product_features, test_actions)


def test_tagvis_catalog_items(check_catalog_visibility, catalog_item):
    """ Checks catalog item tag visibility for restricted user
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag to catalog item
        2. Login as restricted user, catalog item is visible for user
        3. As admin remove tag
        4. Login as restricted user, catalog item is not visible for user

    Polarion:
        assignee: anikifor
        casecomponent: config
        initialEstimate: 1/8h
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

    Polarion:
        assignee: anikifor
        casecomponent: config
        initialEstimate: 1/8h
    """
    check_catalog_visibility(catalog_bundle)


@pytest.mark.uncollectif(lambda appliance: appliance.version < '5.9',
                         reason='Catalog item restriction was not added to 5.8')
def test_restricted_catalog_items_select_for_catalog_bundle(appliance, request, catalog_item,
                                                            user_restricted, tag, soft_assert):
    """Test catalog item restriction while bundle creation

    Polarion:
        assignee: None
        initialEstimate: None
    """
    catalog_bundles = appliance.collections.catalog_bundles
    with user_restricted:
        view = navigate_to(catalog_bundles, 'Add')
        available_options = view.resources.select_resource.all_options
        soft_assert(len(available_options) == 1 and available_options[0].text == '<Choose>', (
            'Catalog item list in not empty, but should be'
        ))
    catalog_item.add_tag(tag)
    request.addfinalizer(lambda: catalog_item.remove_tag(tag))
    with user_restricted:
        view = navigate_to(catalog_bundles, 'Add')
        available_options = view.resources.select_resource.all_options
        soft_assert(any(
            option.text == catalog_item.name for option in available_options), (
            'Restricted catalog item is not visible while bundle creation'))
