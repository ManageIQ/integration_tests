# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from wait_for import wait_for

from cfme import test_requirements
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to


@pytest.fixture(scope="function")
def dialog_cat_item(appliance, catalog):
    service_dialog = appliance.collections.service_dialogs
    dialog = "dialog_{}".format(fauxfactory.gen_alphanumeric())
    ele_name = fauxfactory.gen_alphanumeric()
    element_data = {
        'element_information': {
            'ele_label': "ele_{}".format(fauxfactory.gen_alphanumeric()),
            'ele_name': ele_name,
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Text Box"
        },
        'options': {
            'validation_switch': True,
            'validation': "^([a-z0-9]+_*)*[a-z0-9]+$"
            }
        }
    if appliance.version < '5.10':
        element_data["options"].pop("validation_switch", None)
    sd = service_dialog.create(label=dialog, description="my dialog")
    tab = sd.tabs.create(tab_label="tab_{}".format(fauxfactory.gen_alphanumeric()),
                         tab_desc="my tab desc")
    box = tab.boxes.create(box_label="box_{}".format(fauxfactory.gen_alphanumeric()),
                           box_desc="my box desc")
    box.elements.create(element_data=[element_data])

    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name=fauxfactory.gen_alphanumeric(),
        description="my catalog",
        display_in=True,
        catalog=catalog,
        dialog=sd)
    yield catalog_item, ele_name
    if catalog_item.exists:
        catalog_item.delete()
    sd.delete_if_exists()


@test_requirements.service
def test_dialog_element_regex_validation(appliance, dialog_cat_item):
    """Tests Service Dialog Elements with regex validation.

    Testing BZ 1518971

    Polarion:
        assignee: nansari
        caseimportance: high
        initialEstimate: 1/16h
    """
    catalog_item, ele_name = dialog_cat_item
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    view = navigate_to(service_catalogs, 'Order')
    view.fields(ele_name).fill("!@#%&")
    wait_for(lambda: view.submit_button.disabled, timeout=7)
    view.fields(ele_name).fill("test_123")
    wait_for(lambda: not view.submit_button.disabled, timeout=7)
