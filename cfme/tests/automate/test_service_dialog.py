# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.dialogs.service_dialogs import DialogsView
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.update import update

pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    test_requirements.automate,
    pytest.mark.tier(3)
]


def create_dialog(appliance, element_data, label=None):
    service_dialog = appliance.collections.service_dialogs
    if not label:
        label = "label_{}".format(fauxfactory.gen_alphanumeric())
    sd = service_dialog.create(label=label, description="my dialog")
    tab = sd.tabs.create(tab_label="tab_{}".format(fauxfactory.gen_alphanumeric()),
                         tab_desc="my tab desc")
    box = tab.boxes.create(box_label="box_{}".format(fauxfactory.gen_alphanumeric()),
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
            'ele_label': "ele_{}".format(fauxfactory.gen_alphanumeric()),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
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
            'ele_label': "ele_{}".format(fauxfactory.gen_alphanumeric()),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Text Box"
        },
        'options': {
            'default_text_box': "Default text"
        }
    }
    label = "duplicate_{}".format(fauxfactory.gen_alphanumeric())
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
            'ele_label': "ele_{}".format(fauxfactory.gen_alphanumeric()),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
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
            'ele_label': "ele_{}".format(fauxfactory.gen_alphanumeric()),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
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
            'ele_label': "ele_{}".format(fauxfactory.gen_alphanumeric()),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
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
            'ele_label': "ele_{}".format(fauxfactory.gen_alphanumeric()),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
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
            'ele_label': "ele_label_{}".format(fauxfactory.gen_alphanumeric()),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Text Box",
        }
    }
    element_2_data = {
        'element_information': {
            'ele_label': "ele_{}".format(fauxfactory.gen_alphanumeric()),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Check Box",

        }
    }
    service_dialog = appliance.collections.service_dialogs
    sd = service_dialog.create(label="label_{}".format(fauxfactory.gen_alphanumeric()),
                               description="my dialog")
    tab = sd.tabs.create(tab_label="tab_{}".format(fauxfactory.gen_alphanumeric()),
        tab_desc="my tab desc")
    box = tab.boxes.create(box_label="box_{}".format(fauxfactory.gen_alphanumeric()),
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
    box_label = "box_{}".format(fauxfactory.gen_alphanumeric())
    element_1_data = {
        'element_information': {
            'ele_label': "ele_label_{}".format(fauxfactory.gen_alphanumeric()),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Text Box",
        }
    }
    element_2_data = {
        'element_information': {
            'ele_label': box_label,
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Check Box"
        }
    }
    service_dialog = appliance.collections.service_dialogs
    sd = service_dialog.create(label="label_{}".format(fauxfactory.gen_alphanumeric()),
                               description="my dialog")
    tab = sd.tabs.create(tab_label="tab_{}".format(fauxfactory.gen_alphanumeric()),
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
            'ele_label': "ele_{}".format(fauxfactory.gen_alphanumeric()),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
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
            'ele_label': "ele_{}".format(fauxfactory.gen_alphanumeric()),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
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
            'ele_label': "ele_label_{}".format(fauxfactory.gen_alphanumeric()),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'dynamic_chkbox': True,
            'choose_type': "Text Box",
        }
    }
    service_dialog = appliance.collections.service_dialogs
    sd = service_dialog.create(label='label_{}'.format(fauxfactory.gen_alphanumeric(),
                               description="my dialog"))
    tab = sd.tabs.create(tab_label='tab_{}'.format(fauxfactory.gen_alphanumeric(),
                         tab_desc="my tab desc"))
    box = tab.boxes.create(box_label='box_{}'.format(fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc"))
    assert box.elements.create(element_data=[element_1_data]) is False
    view_cls = navigator.get_class(sd.parent, 'Add').VIEW
    view = appliance.browser.create_view(view_cls)
    assert view.save.disabled


@pytest.mark.manual
@test_requirements.general_ui
@pytest.mark.tier(1)
def test_copying_customization_dialog():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1342260

    Polarion:
        assignee: anikifor
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
