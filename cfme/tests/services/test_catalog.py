# -*- coding: utf-8 -*-
import fauxfactory
import pytest

import cfme.tests.configure.test_access_control as tac
from cfme.utils import error
from cfme.utils.blockers import BZ
from cfme import test_requirements
from cfme.services.catalogs.catalog import Catalog
from cfme.utils.update import update

pytestmark = [test_requirements.service, pytest.mark.tier(2)]


@pytest.mark.sauce
def test_catalog_crud():
    cat = Catalog(name=fauxfactory.gen_alphanumeric(),
                  description="my catalog")
    cat.create()
    with update(cat):
        cat.description = "my edited description"
    cat.delete()


@pytest.mark.sauce
def test_catalog_duplicate_name():
    cat = Catalog(name=fauxfactory.gen_alphanumeric(),
                  description="my catalog")
    cat.create()
    with error.expected("Name has already been taken"):
        cat.create()
    cat.delete()


@pytest.mark.meta(blockers=[BZ(1460891, forced_streams=['5.8', '5.9', 'upstream'])])
@pytest.mark.sauce
def test_permissions_catalog_add(appliance):
    """ Tests that a catalog can be added only with the right permissions"""
    cat = Catalog(name=fauxfactory.gen_alphanumeric(),
                  description="my catalog")

    test_product_features = [['Everything', 'Services', 'Catalogs Explorer', 'Catalogs']]

    # Since we try to create the catalog with the same name, we obliged to delete it after creation
    # in order to avoid "Name has already been taken" error which makes this test "blind" to the
    # fact, that disallowed action actually can be performed.
    # TODO: remove this workaround with "lambda"
    test_actions = {'Add Catalog': lambda _: cat.create(),
                    'Delete Catalog': lambda _: cat.delete()}

    tac.single_task_permission_test(appliance, test_product_features, test_actions)
