import fauxfactory
import pytest
from widgetastic_patternfly import Dropdown

from cfme import test_requirements
from cfme.automate.dialogs.service_dialogs import DialogsView
from cfme.fixtures.automate import DatastoreImport
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.tests.automate.custom_button import TextInputAutomateView
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
    flash_message = f'{dialog.label} was saved'
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


@pytest.mark.meta(automates=[1677724])
@pytest.mark.customer_scenario
@pytest.mark.tier(2)
def test_service_dialogs_crud_non_admin_user(appliance, user_self_service_role):
    """
    Bugzilla:
        1677724

    Polarion:
        assignee: nansari
        startsin: 5.10
        casecomponent: Services
        initialEstimate: 1/6h
        testSteps:
            1. Create a user with tenant admin group
            2. Log in with said user and try to edit/add service dialog
        expectedResults:
            1.
            2.
            3. User should able to perform crud operations
    """
    user, role = user_self_service_role

    product_features = [
        (['Everything'], True), (['Everything'], False),
        (['Everything', 'Automation', 'Automate'], True)
    ]
    role.update({'product_features': product_features})

    with user:
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
        flash_message = f'{dialog.label} was saved'
        view.flash.assert_message(flash_message)
        with update(dialog):
            dialog.description = "my edited description"
        view.flash.assert_message(flash_message)
        dialog.delete()


@pytest.fixture(scope="function")
def custom_button(appliance, import_dialog):
    """This fixture creates custom button for user object"""
    sd, ele_label = import_dialog
    collection = appliance.collections.button_groups

    # Create custom button group
    button_grp = collection.create(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        type=getattr(collection, "USER"),
    )

    # Create custom button
    button = button_grp.buttons.create(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        dialog=sd,
        system="Request",
        request="InspectMe",
    )

    yield button_grp, button
    button.delete_if_exists()
    button_grp.delete_if_exists()


def navigation_to_view(custom_button_group, button):
    """This function helps to navigate to view that comes after clicking on custom button"""
    custom_button_group.item_select(button.text)
    view = button.create_view(TextInputAutomateView, wait="10s")
    return view


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1715396])
@pytest.mark.customer_scenario
@pytest.mark.parametrize(
    "import_data",
    [DatastoreImport("bz_1715396.zip", "bz_1715396", None)],
    ids=["domain"]
)
@pytest.mark.parametrize("file_name", ["bz_1715396.yml"], ids=["dialog"])
def test_dialog_element_values_passed_to_button(appliance, import_datastore, import_data,
                                                custom_button, file_name):
    """
    Bugzilla:
        1715396
        1717501

    Polarion:
        assignee: dgaikwad
        initialEstimate: 1/8h
        startsin: 5.10
        casecomponent: Automate
        testSteps:
            1. Import the attached automate domain and dialog exports in BZ - 1715396. The automate
               domain contains a method to populate the dynamic second element in the dialog.
            2. Put 'Request: InspectMe' or Install object_walker automate domain from
               https://github.com/pemcg/object_walker
            3. Add a custom button to a VM (or any) object. The button should use the newly imported
               BZ dialog, and should run object_walker when submitted (/System/Process: Request,
               Message: create, Request: object_walker)
            4. Click the custom button, and observe the dialog. The element 'Text Box 1' default
               value is empty, the dynamic element 'Text Box 2' has been dynamically populated.
               click on submit button.
            5. Repeat step 4, but type some value(like "aa") in element 'Text Box 1' and click on
               Submit button.
            6. Repeat step 5, but now amend the text dynamically entered into 'Text Box 2'
               (for example adding the string "also").
        expectedResults:
            1.
            2.
            3.
            4. Values passed through to object_walker - both element values should be passed:
               >> ~/object_walker_reader.rb | grep dialog
                     |    $evm.root['dialog_text_box_1'] =    (type: String)
                     |    $evm.root['dialog_text_box_2'] = The dynamic method ran at:
                     2019-05-30 09:42:40 +0100   (type: String)
            5. The value from both test boxes should be passed through object_walker:
                ~/object_walker_reader.rb -t 2019-05-30T09:43:25.558037 | grep dialog
                     |    $evm.root['dialog_text_box_1'] = aa   (type: String)
                     |    $evm.root['dialog_text_box_2'] = The dynamic method ran at:
                     2019-05-30 09:42:43 +0100   (type: String)
            6. Note that both element values are now passed through to object_walker:
                ~/object_walker_reader.rb | grep dialog
                     |    $evm.root['dialog_text_box_1'] = ccdd   (type: String)
                     |    $evm.root['dialog_text_box_2'] = The dynamic method also ran at:
                     2019-05-30 09:50:10 +0100   (type: String)Provision more than 10 VMs
    """
    button_grp, button = custom_button

    user_obj = appliance.collections.users.instantiate(name="Administrator")
    view = navigate_to(user_obj, "Details")
    custom_button_group = Dropdown(view, button_grp.hover)
    view = navigation_to_view(custom_button_group, button)

    # Step 4
    with LogValidator("/var/www/miq/vmdb/log/automation.log",
                      matched_patterns=[".*dialog_text_box_1:      .*",
                                        f".*dialog_text_box_2: {view.text_box2.read()}.*"]
                      ).waiting(timeout=120):
        view.submit.click()

    # Step 5
    view = navigation_to_view(custom_button_group, button)
    msg = fauxfactory.gen_alphanumeric()
    with LogValidator("/var/www/miq/vmdb/log/automation.log",
                      matched_patterns=[f".*dialog_text_box_1: {msg}.*",
                                        f".*dialog_text_box_2: {view.text_box2.read()}.*"]
                      ).waiting(timeout=120):
        view.text_box1.fill(msg)
        view.submit.click()

    # Step 6
    view = navigation_to_view(custom_button_group, button)
    with LogValidator("/var/www/miq/vmdb/log/automation.log",
                      matched_patterns=[f".*dialog_text_box_1: {msg}.*",
                                        f".*dialog_text_box_2: also{view.text_box2.read()}.*"]
                      ).waiting(timeout=120):
        view.text_box1.fill(msg)
        view.text_box2.fill(f"also{view.text_box2.read()}")
        view.submit.click()
