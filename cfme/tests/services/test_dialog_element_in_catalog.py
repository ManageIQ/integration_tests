# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    test_requirements.service,
    pytest.mark.tier(2)
]


@pytest.fixture(scope="function")
def dropdown_dialog(appliance, request):
    service_dialog = appliance.collections.service_dialogs
    dialog = "dialog_" + fauxfactory.gen_alphanumeric()
    element_data ={
        'element_information': {
            'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Dropdown"
        },
        'options': {
            'field_required': True
        }
    }
    sd = service_dialog.create(label=dialog, description="my dialog")
    tab = sd.tabs.create(tab_label='tab_' + fauxfactory.gen_alphanumeric(),
                         tab_desc="my tab desc")
    box = tab.boxes.create(box_label='box_' + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    box.elements.create(element_data=[element_data])
    yield sd
    request.addfinalizer(sd.delete_if_exists)


@pytest.fixture(scope="function")
def catalog_item(request, appliance, dropdown_dialog, catalog):
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name=item_name,
        description="my catalog",
        display_in=True,
        catalog=catalog,
        dialog=dropdown_dialog)
    request.addfinalizer(catalog_item.delete)
    return catalog_item


def test_dropdownlist_required_dialog_element(appliance, catalog_item):
    """Tests service dropdownlist dialog required element.

    Testing BZ 1512398.
    """
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    view = navigate_to(service_catalogs, 'Order')
    assert view.submit_button.disabled
