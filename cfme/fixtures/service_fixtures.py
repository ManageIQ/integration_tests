# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.automate.service_dialogs import DialogCollection
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.catalog_item import CatalogItem


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
