from cfme.services.catalogs.catalog import Catalog
import pytest
import utils.randomness as rand
from utils.update import update
import utils.error as error
import cfme.tests.configure.test_access_control as tac

pytestmark = [pytest.mark.usefixtures("logged_in")]


def test_catalog_crud():
    cat = Catalog(name=rand.generate_random_string(),
                  description="my catalog")
    cat.create()
    with update(cat):
        cat.description = "my edited description"
    cat.delete()


def test_catalog_duplicate_name():
    cat = Catalog(name=rand.generate_random_string(),
                  description="my catalog")
    cat.create()
    with error.expected("Name has already been taken"):
        cat.create()
    cat.delete()


@pytest.mark.bugzilla(1130301)
def test_permissions_catalog_add(setup_cloud_providers):
    """ Tests that a catalog can be added only with the right permissions"""
    cat = Catalog(name=rand.generate_random_string(),
                  description="my catalog")

    def add():
        cat.create()
    tac.single_task_permission_test([['Services', 'Catalogs Explorer', 'Catalogs']],
                                    {'Add Catalog': add})
