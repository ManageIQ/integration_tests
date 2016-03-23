# -*- coding: utf-8 -*-
import fauxfactory
from cfme.services.catalogs.catalog import Catalog
import pytest
from utils.update import update
import utils.error as error
import cfme.tests.configure.test_access_control as tac

pytestmark = [pytest.mark.usefixtures("logged_in")]


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


@pytest.mark.sauce
def test_permissions_catalog_add(setup_cloud_providers):
    """ Tests that a catalog can be added only with the right permissions"""
    cat = Catalog(name=fauxfactory.gen_alphanumeric(),
                  description="my catalog")

    tac.single_task_permission_test([['Everything', 'Services', 'Catalogs Explorer', 'Catalogs']],
                                    {'Add Catalog': cat.create})
