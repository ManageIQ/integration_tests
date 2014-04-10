from cfme.services.catalogs import Catalog
import pytest
import utils.randomness as rand
from utils.update import update
import utils.error as error
import cfme.web_ui.flash as flash


pytestmark = [pytest.mark.usefixtures("logged_in")]


def test_create_catalog():
    cat = Catalog(name=rand.generate_random_string(),
                  description="my catalog")
    cat.create()
    flash.assert_no_errors()


def test_delete_catalog():
    cat = Catalog(name=rand.generate_random_string(),
                  description="my catalog")
    cat.create()
    cat.delete()


def test_update_catalog():
    cat = Catalog(name=rand.generate_random_string(),
                  description="my catalog")
    cat.create()
    with update(cat):
        cat.description = "my edited description"
    flash.assert_no_errors()


def test_catalog_duplicate_name():
    cat = Catalog(name=rand.generate_random_string(),
                  description="my catalog")
    cat.create()
    with error.expected("Name has already been taken"):
        cat.create()
