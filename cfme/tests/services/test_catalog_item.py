from cfme.services.catalogs import CatalogItem
import pytest
import utils.randomness as rand
from utils.update import update
import utils.error as error
import cfme.web_ui.flash as flash


pytestmark = [pytest.mark.usefixtures("logged_in")]


def test_create_catalog_item():

    cat_item = CatalogItem(item_type="VMware", name=rand.generate_random_string(),
                  description="my catalog", display_in=True, catalog="auto_cat_1MnAggj0", dialog="auto_dialog_1MnAggj0")
    cat_item.create()
    flash.assert_no_errors()


