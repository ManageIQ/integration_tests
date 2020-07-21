import fauxfactory
import pytest
from wait_for import wait_for

from cfme import test_requirements
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    test_requirements.dialog,
    pytest.mark.tier(2)
]


@pytest.fixture(scope="function")
def dialog_cat_item(appliance, catalog, request):

    service_dialog = appliance.collections.service_dialogs
    dialog = fauxfactory.gen_alphanumeric(12, start="dialog_")

    element_data = {
        'element_information': {
            'ele_label': fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            'ele_name': fauxfactory.gen_alphanumeric(15, start="ele_name_"),
            'ele_desc': fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            'choose_type': "Text Box"
        },
        'options': {
            'validation_switch': True,
            'validation': request.param["validation"]
        }
    }

    if appliance.version < '5.10':
        element_data["options"].pop("validation_switch", None)
    sd = service_dialog.create(label=dialog, description="my dialog")
    tab = sd.tabs.create(tab_label=fauxfactory.gen_alphanumeric(start="tab_"),
                         tab_desc="my tab desc")
    box = tab.boxes.create(box_label=fauxfactory.gen_alphanumeric(start="box_"),
                           box_desc="my box desc")
    box.elements.create(element_data=[element_data])

    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name=fauxfactory.gen_alphanumeric(15, start="cat_item_"),
        description="my catalog",
        display_in=True,
        catalog=catalog,
        dialog=sd)
    yield catalog_item, element_data, sd
    if catalog_item.exists:
        catalog_item.delete()
    sd.delete_if_exists()


@pytest.mark.parametrize("dialog_cat_item", [{"validation": "^([a-z0-9]+_*)*[a-z0-9]+$"}],
                         indirect=True)
def test_dialog_element_regex_validation(appliance, dialog_cat_item):
    """Tests Service Dialog Elements with regex validation.

    Testing BZ 1518971

    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: high
        initialEstimate: 1/16h
    """
    catalog_item, element_data, sd = dialog_cat_item
    ele_name = element_data["element_information"]["ele_name"]
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    view = navigate_to(service_catalogs, 'Order')
    view.fields(ele_name).fill("!@#%&")
    wait_for(lambda: view.submit_button.disabled, timeout=7)
    view.fields(ele_name).fill("test_123")
    wait_for(lambda: not view.submit_button.disabled, timeout=7)


@pytest.mark.manual
@pytest.mark.tier(1)
def test_dialog_text_area_element_regex_validation():
    """ Tests Service Dialog Elements with regex validation

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        startsin: 5.10
        caseimportance: high
        testSteps:
            1. Create a dialog. Set regex_validation in text area
            2. Use the dialog in a catalog.
            3. Order catalog.
        expectedResults:
            1.
            2.
            3. Regex validation should work
    """
    pass


@pytest.mark.meta(automates=[1720245])
@pytest.mark.ignore_stream("5.10")
@pytest.mark.tier(2)
@pytest.mark.parametrize("dialog_cat_item", [{"validation": "^[0-9]*$"}],
                         indirect=True)
def test_dialog_regex_validation_button(appliance, dialog_cat_item):
    """
    Bugzilla:
        1720245
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/16h
        startsin: 5.11
        testSteps:
            1. Add dialog with Regular Expression - "^[0-9]*$"
            2. Create catalog and catalog item
            3. Navigate to Order page of the service
            4. Type "a" and it will show a message that does not satisfy the regex.
            5. Clear the field
        expectedResults:
            1.
            2.
            3.
            4.
            5. Submit button should have become active when the validate field cleared
    """
    catalog_item, element_data, sd = dialog_cat_item
    ele_name = element_data["element_information"]["ele_name"]
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    view = navigate_to(service_catalogs, 'Order')

    view.fields(ele_name).fill("a")
    element = view.fields(ele_name).input
    msg = f"""Entered text should match the format: {element_data["options"]["validation"]}"""
    assert element.warning == msg
    wait_for(lambda: view.submit_button.disabled, timeout=10)

    view.fields(ele_name).fill("")
    wait_for(lambda: view.submit_button.is_enabled, timeout=10)


@pytest.mark.meta(coverage=[1721814])
@pytest.mark.manual
@pytest.mark.ignore_stream('5.10')
@pytest.mark.tier(2)
def test_regex_dialog_validation_error():
    """
    Bugzilla:
        1721814
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/16h
        startsin: 5.11
        testSteps:
            1. Create a dialog. Set regex_validation in text box ->  ^[0-9]*$
            2. Save the dialog
            3. Edit the dialog and disable the validation button of text box
            4. Use the dialog in a catalog
            5. Navigate to catalog order page
            6. Input anything except the format " ^[0-9]*$ "
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6. It shouldn't gives the validation error
    """
    pass
