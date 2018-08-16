# -*- coding: utf-8 -*-
import fauxfactory
import pytest

import cfme.tests.configure.test_access_control as tac
from cfme import test_requirements
from cfme.services.catalogs.catalog import CatalogsView
from cfme.utils.blockers import BZ
from cfme.utils.update import update

pytestmark = [test_requirements.service, pytest.mark.tier(2)]


@pytest.mark.rhel_testing
@pytest.mark.sauce
def test_catalog_crud(appliance):
    catalog_name = fauxfactory.gen_alphanumeric()
    cat = appliance.collections.catalogs.create(name=catalog_name, description='my catalog')

    view = cat.create_view(CatalogsView)
    assert view.is_displayed
    view.flash.assert_success_message('Catalog "{}" was saved'.format(catalog_name))

    with update(cat):
        cat.description = 'my edited description'
    cat.delete()


@pytest.mark.sauce
def test_catalog_duplicate_name(appliance):
    catalog_name = fauxfactory.gen_alphanumeric()
    cat = appliance.collections.catalogs.create(name=catalog_name, description='my catalog')
    with pytest.raises(AssertionError):
        appliance.collections.catalogs.create(name=catalog_name, description='my catalog')
    view = cat.create_view(CatalogsView)
    view.flash.assert_message('Name has already been taken')
    cat.delete()


@pytest.mark.meta(blockers=[BZ(1460891, forced_streams=['5.8', '5.9', 'upstream'])])
@pytest.mark.sauce
def test_permissions_catalog_add(appliance):
    """ Tests that a catalog can be added only with the right permissions"""
    # This test needs to retain a reference to the catalog created when `_create_catalog` is run
    # from within `single_task_permission_test`, so we use a list so that we don't have to use all
    # sorts of global variables. This list will only ever have 1 item in it.
    catalogs = []

    def _create_catalog():
        catalogs.append(appliance.collections.catalogs.create(name=fauxfactory.gen_alphanumeric(),
                                                              description="my catalog"))

    def _delete_catalog():
        if catalogs:
            # See comment above list declaration for why only the first item is deleted
            catalogs[0].delete()

    test_product_features = [['Everything', 'Services', 'Catalogs Explorer', 'Catalogs']]

    # Since we try to create the catalog with the same name, we obliged to delete it after creation
    # in order to avoid "Name has already been taken" error which makes this test "blind" to the
    # fact, that disallowed action actually can be performed.
    # TODO: remove this workaround with "lambda"
    test_actions = {'Add Catalog': _create_catalog,
                    'Delete Catalog': _delete_catalog}

    tac.single_task_permission_test(appliance, test_product_features, test_actions)
