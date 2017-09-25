# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.services.service_catalogs import ServiceCatalogs  # NOQA
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.web_ui import AngularSelect, fill
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.version import current_version


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda: current_version() < "5.5.0.7")
@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(blockers=[1274665])
def test_broken_angular_select(appliance, request):
    """Test that checks the fancy selects do not break.

    Prerequisities:
        * A fresh downstream appliance

    Steps:
        1) Create a catalog.
        2) Create a catalog item, can be Generic and assign the catalog and OSE Installer dialog
            for testing purposes
        3) Try ordering the service, but instead of confirming the form, try changing some select.
    """
    # OSE Installer dialog, one dropdown from it
    the_select = AngularSelect("param_operatingSystemType")
    cat = Catalog("Test_catalog_{}".format(fauxfactory.gen_alpha()))
    cat.create()
    request.addfinalizer(cat.delete)
    item = CatalogItem(
        item_type="Generic",
        name="Catitem_{}".format(fauxfactory.gen_alpha()),
        description=fauxfactory.gen_alpha(),
        display_in=True,
        catalog=cat,
        dialog="azure-single-vm-from-user-image")
    item.create()
    request.addfinalizer(item.delete)
    sc = ServiceCatalogs(appliance, item.catalog, item.name)
    navigate_to(sc, 'Order')
    # The check itself
    fill(the_select, "Linux")
    assert not the_select.is_broken, "The select displayed itself next ot the angular select"
