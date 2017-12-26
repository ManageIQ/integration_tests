# -*- coding: utf-8 -*-
import fauxfactory
import pytest

import cfme.tests.configure.test_access_control as tac

from cfme import test_requirements
from cfme.services.catalogs.catalog import Catalog
from cfme.utils import error
from cfme.utils.blockers import BZ
from cfme.utils.update import update
from cfme.utils.version import current_version

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


# Un-collecting for 5.8 because of BZ: 1486041
@pytest.mark.uncollectif(lambda: current_version() < '5.9')
@pytest.mark.meta(blockers=[BZ(1529079, forced_streams=['upstream'])])
@pytest.mark.sauce
def test_permissions_catalog_add(appliance):
    """ Tests that a catalog can be added only with the right permissions"""
    cat = Catalog(name=fauxfactory.gen_alphanumeric(),
                  description="my catalog")

    tac.single_task_permission_test(appliance,
                                    [['Everything', 'Services', 'Catalogs Explorer', 'Catalogs']],
                                    {'Add Catalog': cat.create})
