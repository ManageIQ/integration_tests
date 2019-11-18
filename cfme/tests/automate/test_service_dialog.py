import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.dialogs.service_dialogs import DialogsView
from cfme.fixtures.automate import DatastoreImport
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log_validator import LogValidator
from cfme.utils.update import update

pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    test_requirements.dialog,
    pytest.mark.tier(3)
]


def create_dialog(appliance, element_data, label=None):
    service_dialog = appliance.collections.service_dialogs
    if not label:
        label = fauxfactory.gen_alphanumeric(15, start="label_")
    sd = service_dialog.create(label=label, description="my dialog")
    tab = sd.tabs.create(tab_label=fauxfactory.gen_alphanumeric(start="tab_"),
                         tab_desc="my tab desc")
    box = tab.boxes.create(box_label=fauxfactory.gen_alphanumeric(start="box_"),
                           box_desc="my box desc")
    element = box.elements.create(element_data=[element_data])
    return sd, element


@pytest.mark.sauce
def test_crud_service_dialog(appliance):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """
    element_data = {
        'element_information': {
            'ele_label': fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            'ele_name': fauxfactory.gen_alphanumeric(15, start="ele_name_"),
            'ele_desc': fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            'choose_type': "Text Box"
        },
        'options': {
            'default_text_box': "Default text"
        }
    }

    dialog, element = create_dialog(appliance, element_data)
    view = appliance.browser.create_view(DialogsView, wait="10s")
    flash_message = '{} was saved'.format(dialog.label)
    view.flash.assert_message(flash_message)
    with update(dialog):
        dialog.description = "my edited description"
    view.flash.assert_message(flash_message)
    dialog.delete()


def test_service_dialog_duplicate_name(appliance, request):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: low
        initialEstimate: 1/8h
        tags: service
    """
    element_data = {
        'element_information': {
            'ele_label': fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            'ele_name': fauxfactory.gen_alphanumeric(15, start="ele_name_"),
            'ele_desc': fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            'choose_type': "Text Box"
        },
        'options': {
            'default_text_box': "Default text"
        }
    }
    label = fauxfactory.gen_alphanumeric(15, start="duplicate_")
    dialog, element = create_dialog(appliance, element_data, label=label)
    request.addfinalizer(dialog.delete_if_exists)
    region_number = appliance.server.zone.region.number

    d = "" if appliance.version < "5.10" else "Dialog: "
    error_message = (
        "There was an error editing this dialog: "
        "Failed to create a new dialog - Validation failed: "
        "{d}Name is not unique within region {reg_num}"
    ).format(d=d, reg_num=region_number)

    with pytest.raises(AssertionError, match=error_message):
        create_dialog(appliance, element_data, label=label)


def test_checkbox_dialog_element(appliance, request):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: low
        initialEstimate: 1/8h
        tags: service
    """
    element_data = {
        'element_information': {
            'ele_label': fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            'ele_name': fauxfactory.gen_alphanumeric(15, start="ele_name_"),
            'ele_desc': fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            'choose_type': "Check Box"
        },
        'options': {
            'default_value': True,
            'field_required': True
        }
    }
    dialog, element = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_datecontrol_dialog_element(appliance, request):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/8h
        tags: service
    """

    element_data = {
        'element_information': {
            'ele_label': fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            'ele_name': fauxfactory.gen_alphanumeric(15, start="ele_name_"),
            'ele_desc': fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            'choose_type': "Datepicker"
        },
        'options': {
            'field_past_dates': True
        }
    }
    dialog, element = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_tagcontrol_dialog_element(appliance, request):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/8h
        tags: service
    """
    element_data = {
        'element_information': {
            'ele_label': fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            'ele_name': fauxfactory.gen_alphanumeric(15, start="ele_name_"),
            'ele_desc': fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            'choose_type': "Tag Control"
        },
        'options': {
            'field_category': "Service Level",
            'field_required': "Yes"
        }
    }
    dialog, element = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_textareabox_dialog_element(appliance, request):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/8h
        tags: service
    """

    element_data = {
        'element_information': {
            'ele_label': fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            'ele_name': fauxfactory.gen_alphanumeric(15, start="ele_name_"),
            'ele_desc': fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            'choose_type': "Text Area",
        },
        'options': {
            'field_required': "Yes"
        }
    }
    dialog, element = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_reorder_elements(appliance, request):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/8h
        tags: service
    """
    element_1_data = {
        'element_information': {
            'ele_label': fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            'ele_name': fauxfactory.gen_alphanumeric(15, start="ele_name_"),
            'ele_desc': fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            'choose_type': "Text Box",
        }
    }
    element_2_data = {
        'element_information': {
            'ele_label': fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            'ele_name': fauxfactory.gen_alphanumeric(15, start="ele_name_"),
            'ele_desc': fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            'choose_type': "Check Box",

        }
    }
    service_dialog = appliance.collections.service_dialogs
    sd = service_dialog.create(label=fauxfactory.gen_alphanumeric(start="label_"),
                               description="my dialog")
    tab = sd.tabs.create(tab_label=fauxfactory.gen_alphanumeric(start="tab_"),
        tab_desc="my tab desc")
    box = tab.boxes.create(box_label=fauxfactory.gen_alphanumeric(start="box_"),
        box_desc="my box desc")
    element = box.elements.create(element_data=[element_1_data, element_2_data])
    request.addfinalizer(sd.delete_if_exists)
    element.reorder_elements(False, element_2_data, element_1_data)


def test_reorder_unsaved_elements(appliance, request):
    """
    Bugzilla:
        1238721

    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: low
        initialEstimate: 1/16h
        tags: service
    """
    box_label = fauxfactory.gen_alphanumeric(start="box_")
    element_1_data = {
        'element_information': {
            'ele_label': fauxfactory.gen_alphanumeric(15, start="ele1_label_"),
            'ele_name': fauxfactory.gen_alphanumeric(15, start="ele1_name_"),
            'ele_desc': fauxfactory.gen_alphanumeric(15, start="ele1_desc_"),
            'choose_type': "Text Box",
        }
    }
    element_2_data = {
        'element_information': {
            'ele_label': box_label,
            'ele_name': fauxfactory.gen_alphanumeric(15, start="ele2_name_"),
            'ele_desc': fauxfactory.gen_alphanumeric(15, start="ele2_desc_"),
            'choose_type': "Check Box"
        }
    }
    service_dialog = appliance.collections.service_dialogs
    sd = service_dialog.create(label=fauxfactory.gen_alphanumeric(start="label_"),
                               description="my dialog")
    tab = sd.tabs.create(tab_label=fauxfactory.gen_alphanumeric(start="tab_"),
        tab_desc="my tab desc")
    box = tab.boxes.create(box_label=box_label,
        box_desc="my box desc")
    element = box.elements.create(element_data=[element_1_data])
    request.addfinalizer(sd.delete_if_exists)
    element.reorder_elements(True, element_2_data, element_1_data)


def test_dropdownlist_dialog_element(appliance, request):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: low
        initialEstimate: 1/4h
        tags: service
    """

    element_data = {
        'element_information': {
            'ele_label': fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            'ele_name': fauxfactory.gen_alphanumeric(15, start="ele_name_"),
            'ele_desc': fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            'choose_type': "Dropdown"
        }
    }
    dialog, element = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_radiobutton_dialog_element(appliance, request):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: low
        initialEstimate: 1/4h
        tags: service
    """
    element_data = {
        'element_information': {
            'ele_label': fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            'ele_name': fauxfactory.gen_alphanumeric(15, start="ele_name_"),
            'ele_desc': fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            'choose_type': "Radio Button"
        }
    }
    dialog, element = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_mandatory_entry_point_with_dynamic_element(appliance):
    """Tests Entry point should be mandatory if element is dynamic

    Bugzilla:
        1488579

    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: high
        initialEstimate: 1/8h
        tags: service
    """
    element_1_data = {
        'element_information': {
            'ele_label': fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            'ele_name': fauxfactory.gen_alphanumeric(15, start="ele_name_"),
            'ele_desc': fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            'dynamic_chkbox': True,
            'choose_type': "Text Box",
        }
    }
    service_dialog = appliance.collections.service_dialogs
    sd = service_dialog.create(label=fauxfactory.gen_alphanumeric(start="label_"),
                               description="my dialog")
    tab = sd.tabs.create(tab_label=fauxfactory.gen_alphanumeric(start="tab_"),
                         tab_desc="my tab desc")
    box = tab.boxes.create(box_label=fauxfactory.gen_alphanumeric(start="box_"),
                           box_desc="my box desc")
    assert box.elements.create(element_data=[element_1_data]) is False
    view_cls = navigator.get_class(sd.parent, 'Add').VIEW
    view = appliance.browser.create_view(view_cls)
    assert view.save.disabled


@pytest.mark.manual
@test_requirements.general_ui
@pytest.mark.tier(1)
def test_copying_customization_dialog():
    """
    Bugzilla:
        1342260

    Polarion:
        assignee: pvala
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/12h
        testSteps:
            1. Automate -> Customization -> Check checkbox for at least one dialog
            2. Select another dialog by clicking on it
            3. Select in Toolbar Configuration -> Copy this dialog
            4. Selected dialog should be copied and not the first checked dialog
            in alphanumerical sort
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(1)
def test_default_value_on_dropdown_inside_dialog():
    """
    Test default value of a dropdown element in the service dialog.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        testSteps:
            1. Create new service dialog (Automation > Automate > Customization > Service Dialog)
            2. Select a dropdown element and add it to the dialog
            3. In dropdown settings on Options tab, make sure there are multiple key/value entries
            4. On the same tab, select a 'Default value' for the dropdown element and save
            5. Navigate Automation > Automate > Customization > Service Dialog and select the
                newly created dialog
            6. Make sure the default value is displayed on the dropdown element
        expectedResults:
            4. Dialog created and saved successfully
            6. Correct default value displayed on the dropdown element
    Bugzilla:
        1516721
    """
    pass


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(1)
def test_dialog_items_default_values_on_different_screens():
    """
    Bugzilla:
        1540273

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.meta(automates=[1571000])
@pytest.mark.tier(3)
@pytest.mark.customer_scenario
@pytest.mark.parametrize(
    "import_data",
    [DatastoreImport("bz_1571000.zip", "bz_1571000", None)],
    ids=["domain"]
)
@pytest.mark.parametrize("file_name", ["bz_1571000.yml"], ids=["dialog"])
def test_automate_methods_from_dynamic_dialog_should_run_as_per_designed(
    request, appliance, import_datastore, import_data, import_dialog, catalog, soft_assert
):
    """
    Bugzilla:
        1571000

    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/16h
        startsin: 5.9
        tags: service
    """
    sd, ele_label = import_dialog
    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        display_in=True,
        catalog=catalog,
        dialog=sd,
    )
    request.addfinalizer(catalog_item.delete_if_exists)
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    patterns = [
        ".*CC- dialog_instance1 value=.*",
        ".*CC- dialog_instance2 value=.*",
        ".*CC- dialog_instance3 value=.*",
    ]

    # Checking if automates method gets triggered by three instances for once after ordering catalog
    # item
    result = LogValidator(
        "/var/www/miq/vmdb/log/automation.log", matched_patterns=patterns
    )
    result.start_monitoring()
    view = navigate_to(service_catalogs, "Order")
    for pattern in patterns:
        soft_assert(result.matches[pattern] == 1)

    with LogValidator("/var/www/miq/vmdb/log/automation.log", failure_patterns=patterns).waiting(
        timeout=120
    ):
        # Values like 'label1'(value of ele_label), 'label2' and label3 are element names of three
        # different text boxes attached with service dialog
        for ele_name in [ele_label, "label2", "label3"]:
            # Checking if automate method is not triggered after updating values of dialog widgets
            view.fields(ele_name).input.fill(fauxfactory.gen_alphanumeric())
