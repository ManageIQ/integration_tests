# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.services.catalogs import service_catalogs  # NOQA
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.web_ui import AngularSelect, fill
from utils.version import current_version


TOLERANCE = 20
# TODO: Replace nav branch strings with navmazing object destinations when supported
LOCATIONS = [
    "control_explorer", "automate_explorer", "automate_customization", "my_services",
    # "services_catalogs",
    "services_workloads", "reports", "chargeback", "clouds_instances",
    "infrastructure_virtual_machines", "infrastructure_pxe", "configuration"]


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda: current_version() < "5.5.0.7")
@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(blockers=[1274665])
def test_broken_angular_select(request):
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
    the_select = AngularSelect("ose_size")
    cat = Catalog("Test_catalog_{}".format(fauxfactory.gen_alpha()))
    cat.create()
    request.addfinalizer(cat.delete)
    item = CatalogItem(
        item_type="Generic",
        name="Catitem_{}".format(fauxfactory.gen_alpha()),
        description=fauxfactory.gen_alpha(),
        display_in=True,
        catalog=cat.name,
        dialog="OSE Installer")
    item.create()
    request.addfinalizer(item.delete)

    # The check itself
    pytest.sel.force_navigate(
        "order_service_catalog",
        context={"catalog": cat.name, "catalog_item": item})
    fill(the_select, "Medium")
    assert not the_select.is_broken, "The select displayed itself next ot the angular select"
