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


def test_dialog_element_regex_validation(appliance, dialog_cat_item):
    """Tests Service Dialog Elements with regex validation.

    Testing BZ 1518971

    Polarion:
        assignee: nansari
        casecomponent: Services
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


@pytest.mark.meta(coverage=[1720245])
@pytest.mark.manual
@pytest.mark.ignore_stream('5.10')
@pytest.mark.tier(2)
def test_dialog_regex_validation_button():
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
    pass


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
