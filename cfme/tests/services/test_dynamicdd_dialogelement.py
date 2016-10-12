# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.automate.explorer import Domain, Namespace, Class, Method, Instance
from cfme import test_requirements

pytestmark = [
    pytest.mark.long_running,
    test_requirements.service,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.meta(server_roles="+automate")
]

item_name = fauxfactory.gen_alphanumeric()

METHOD_TORSO = """
# Method for logging
def log(level, message)
  @method = 'Service Dialog Provider Select'
  $evm.log(level, "#{@method} - #{message}")
end

# Start Here
log(:info, " - Listing Root Object Attributes:") if @debug
$evm.root.attributes.sort.each { |k, v| $evm.log('info', "#{@method} - \t#{k}: #{v}") if @debug }
log(:info, "===========================================") if @debug

        dialog_field = $evm.object
        dialog_field['data_type'] = 'string'
        dialog_field['required']  = 'true'
        dialog_field['sort_by']   = 'value'
        dialog_field["values"] = [[1, "one"], [2, "two"], [10, "ten"], [50, "fifty"]]
"""


@pytest.yield_fixture(scope="function")
def dialog(copy_instance, create_method):
    dialog = "dialog_" + fauxfactory.gen_alphanumeric()
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Drop Down List",
        'dynamic_chkbox': True
    }
    dialog = ServiceDialog(label="dialog_" + fauxfactory.gen_alphanumeric(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                           tab_desc="my tab desc",
                           box_label="box_" + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    dialog.create(element_data)
    yield dialog


@pytest.yield_fixture(scope="function")
def catalog():
    cat_name = "cat_" + fauxfactory.gen_alphanumeric()
    catalog = Catalog(name=cat_name,
                  description="my catalog")
    catalog.create()
    yield catalog


@pytest.fixture(scope="function")
def copy_domain(request):
    domain = Domain(name="new_domain", enabled=True)
    domain.create()
    request.addfinalizer(lambda: domain.delete() if domain.exists() else None)
    return domain


@pytest.fixture(scope="function")
def create_method(request, copy_domain):
    method = Method(
        name="InspectMe",
        data=METHOD_TORSO,
        cls=Class(
            name="Request",
            namespace=Namespace(
                name="System",
                parent=copy_domain
            )
        )
    )
    method.create()
    return method


@pytest.fixture(scope="function")
def copy_instance(request, copy_domain):
    miq_domain = Domain(name="ManageIQ (Locked)", enabled=True)
    instance = Instance(
        name="InspectMe",
        cls=Class(
            name="Request",
            namespace=Namespace(
                name="System",
                parent=miq_domain
            )
        )
    )
    instance.copy_to(copy_domain)


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1219950])
def test_dynamicdropdown_dialog(dialog, catalog):
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type="Generic", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog.name,
                  dialog=dialog.label)
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_item)
