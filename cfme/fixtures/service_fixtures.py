# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.automate.service_dialogs import DialogCollection
from cfme.common.provider import cleanup_vm
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.services.requests import Request
from cfme.utils.log import logger


@pytest.yield_fixture(scope="function")
def dialog(appliance):
    service_dialogs = DialogCollection(appliance)
    dialog = fauxfactory.gen_alphanumeric()
    element_data = dict(
        ele_label="ele_" + fauxfactory.gen_alphanumeric(),
        ele_name="service_name",
        ele_desc="my ele desc",
        choose_type="Text Box",
        default_text_box=dialog
    )

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
    catalog = "cat_" + fauxfactory.gen_alphanumeric()
    cat = Catalog(name=catalog,
                  description="my catalog")
    cat.create()
    yield cat


@pytest.fixture(scope="function")
def catalog_item(provider, provisioning, vm_name, dialog, catalog):
    template, host, datastore, iso_file, catalog_item_type, vlan = map(provisioning.get,
        ('template', 'host', 'datastore', 'iso_file', 'catalog_item_type', 'vlan'))
    item_name = dialog.label
    provisioning_data = dict(
        vm_name=vm_name,
        host_name={'name': [host]},
        datastore_name={'name': [datastore]},
        vlan=vlan
    )

    if provider.type == 'rhevm':
        provisioning_data['provision_type'] = 'Native Clone'
    elif provider.type == 'virtualcenter':
        provisioning_data['provision_type'] = 'VMware'
    catalog_item = CatalogItem(item_type=catalog_item_type, name=item_name,
                  description="my catalog", display_in=True, catalog=catalog,
                  dialog=dialog, catalog_name=template,
                  provider=provider, prov_data=provisioning_data)
    return catalog_item


@pytest.fixture(scope="function")
def order_catalog_item_in_ops_ui(appliance, provider, catalog_item, request):
    """
        Fixture for SSUI tests.
        Orders catalog item in OPS UI.
    """
    vm_name = catalog_item.provisioning_data["vm_name"]
    request.addfinalizer(lambda: cleanup_vm("{}_0001".format(vm_name), provider))
    catalog_item.create()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info("Waiting for cfme provision request for service {}".format(catalog_item.name))
    request_description = catalog_item.name
    provision_request = Request(request_description, partial_check=True)
    provision_request.wait_for_request()
    assert provision_request.is_finished()
    return catalog_item.name
