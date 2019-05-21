# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    test_requirements.dialog,
    pytest.mark.tier(2)
]


@pytest.fixture(scope="function")
def dropdown_dialog(appliance, request):
    service_dialog = appliance.collections.service_dialogs
    dialog = "dialog_" + fauxfactory.gen_alphanumeric()
    element_data = {
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

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        testtype: functional
        casecomponent: Services
        startsin: 5.10
    """
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    view = navigate_to(service_catalogs, 'Order')
    assert view.submit_button.disabled


@pytest.mark.manual
@pytest.mark.tier(1)
@pytest.mark.parametrize('element_type', ['text_box', 'checkbox', 'text_area', 'radiobutton',
                                          'date_picker', 'timepicker', 'tagcontrol'])
def test_required_dialog_elements(element_type):
    """ Tests service text_box dialog required element
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        caseimportance: high
        startsin: 5.10
        testSteps:
            1. Create a dialog. Set required true to element
            2. Use the dialog in a catalog.
            3. Order catalog.
         expectedResults:
            1.
            2.
            3. Submit button should be disabled
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_validate_not_required_dialog_element():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        caseimportance: high
        startsin: 5.10
        testSteps:
            1. Create a dialog with a field which needs to 'Validate' but is not 'Required'
            2. Execute the dialog as a Catalog Service
            3. Try submitting the dialog only with the 'Required' Fields
        expectedResults:
            1.
            2.
            3. It should be able to submit the form with only 'Required' fields

    Bugzilla:
        1692736
    """
    pass
