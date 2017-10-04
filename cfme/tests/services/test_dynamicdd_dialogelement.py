# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.automate.explorer.domain import DomainCollection
from cfme.automate.service_dialogs import DialogCollection
from cfme.services.catalogs.catalog import Catalog
from cfme.services.service_catalogs import ServiceCatalogs
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
def dialog(appliance, copy_instance, create_method):
    service_dialogs = DialogCollection(appliance)
    dialog = "dialog_" + fauxfactory.gen_alphanumeric()
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Drop Down List",
        'dynamic_chkbox': True
    }
    sd = service_dialogs.create(label=dialog,
        description="my dialog", submit=True, cancel=True,)
    tab = sd.tabs.create(tab_label='tab_' + fauxfactory.gen_alphanumeric(),
        tab_desc="my tab desc")
    box = tab.boxes.create(box_label='box_' + fauxfactory.gen_alphanumeric(),
        box_desc="my box desc")
    box.elements.create(element_data=[element_data])
    yield sd


@pytest.yield_fixture(scope="function")
def catalog():
    cat_name = "cat_" + fauxfactory.gen_alphanumeric()
    catalog = Catalog(name=cat_name,
                  description="my catalog")
    catalog.create()
    yield catalog


@pytest.fixture(scope="function")
def copy_domain(request, appliance):
    domain = DomainCollection(appliance).create(name="new_domain", enabled=True)
    request.addfinalizer(domain.delete_if_exists)
    return domain


@pytest.fixture(scope="function")
def create_method(request, copy_domain):
    return copy_domain\
        .namespaces.instantiate(name='System')\
        .classes.instantiate(name='Request')\
        .methods.create(
            name='InspectMe',
            location='inline',
            script=METHOD_TORSO)


@pytest.fixture(scope="function")
def copy_instance(request, copy_domain, appliance):
    miq_domain = DomainCollection(appliance).instantiate(name='ManageIQ')
    instance = miq_domain\
        .namespaces.instantiate(name='System')\
        .classes.instantiate(name='Request')\
        .instances.instantiate(name='InspectMe')
    instance.copy_to(copy_domain)


@pytest.mark.tier(3)
def test_dynamicdropdown_dialog(appliance, dialog, catalog):
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type="Generic", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog,
                  dialog=dialog)
    catalog_item.create()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
