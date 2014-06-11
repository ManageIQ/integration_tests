from cfme.services.catalogs.catalog import Catalog
import pytest
import utils.randomness as rand
from utils.update import update
import utils.error as error
from utils import rest
from utils.wait import wait_for


pytestmark = [pytest.mark.usefixtures("logged_in")]


def test_catalog_crud():
    cat = Catalog(name=rand.generate_random_string(),
                  description="my catalog")
    cat.create()
    wait_for(
        lambda: len(
            rest.GET(
                "/service_catalogs", sqlfilter="name = '{}'".format(cat.name))["resources"]) == 1,
        num_sec=30, delay=0.2)
    with update(cat):
        cat.description = "my edited description"
    cat.delete()
    wait_for(
        lambda: len(
            rest.GET(
                "/service_catalogs", sqlfilter="name = '{}'".format(cat.name))["resources"]) == 0,
        num_sec=30, delay=0.2)


def test_catalog_duplicate_name():
    cat = Catalog(name=rand.generate_random_string(),
                  description="my catalog")
    cat.create()
    with error.expected("Name has already been taken"):
        cat.create()
    cat.delete()
