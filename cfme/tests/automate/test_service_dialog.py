# -*- coding: utf-8 -*-
import pytest
import fauxfactory

from cfme import test_requirements
from cfme.automate.service_dialogs import DialogCollection
from cfme.utils.update import update
from cfme.utils import version, error

pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    test_requirements.automate,
    pytest.mark.tier(3)
]


def create_dialog(appliance, element_data, label=None):
    service_dialog = DialogCollection(appliance)
    if label is None:
        label = 'label_' + fauxfactory.gen_alphanumeric()
    sd = service_dialog.create(label=label,
        description="my dialog", submit=True, cancel=True,)
    tab = sd.tabs.create(tab_label='tab_' + fauxfactory.gen_alphanumeric(),
        tab_desc="my tab desc")
    box = tab.boxes.create(box_label='box_' + fauxfactory.gen_alphanumeric(),
        box_desc="my box desc")
    box.elements.create(element_data=[element_data])
    return sd


def test_crud_service_dialog(appliance):
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }

    dialog = create_dialog(appliance, element_data)
    with update(dialog):
        dialog.description = "my edited description"
    dialog.delete()


def test_service_dialog_duplicate_name(appliance, request):
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }
    label = 'duplicate_' + fauxfactory.gen_alphanumeric()
    dialog = create_dialog(appliance, element_data, label=label)
    request.addfinalizer(dialog.delete_if_exists)
    error_message = version.pick({
        '5.8': 'Validation failed: Label is not unique within region 0',
        '5.7': 'Label has already been taken'})
    with error.expected(error_message):
        create_dialog(appliance, element_data, label=label)


def test_checkbox_dialog_element(appliance, request):
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Check Box",
        'default_value': True,
        'field_required': True
    }
    dialog = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_datecontrol_dialog_element(appliance, request):
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Date Control",
        'field_past_dates': True
    }
    dialog = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_dropdownlist_dialog_element(appliance, request):
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Drop Down List"
    }
    dialog = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_radiobutton_dialog_element(appliance, request):
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Radio Button"
    }
    dialog = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_tagcontrol_dialog_element(appliance, request):
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Tag Control",
        'field_category': "Service Level",
        'field_required': True
    }
    dialog = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_textareabox_dialog_element(appliance, request):
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Text Area Box",
        'field_required': True
    }
    dialog = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_reorder_elements(appliance, request):
    element_1_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }
    element_2_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Check Box",
        'default_value': True,
        'field_required': True,
    }
    service_dialog = DialogCollection(appliance)
    sd = service_dialog.create(label='label_' + fauxfactory.gen_alphanumeric(),
        description="my dialog", submit=True, cancel=True,)
    tab = sd.tabs.create(tab_label='tab_' + fauxfactory.gen_alphanumeric(),
        tab_desc="my tab desc")
    box = tab.boxes.create(box_label='box_' + fauxfactory.gen_alphanumeric(),
        box_desc="my box desc")
    element = box.elements.create(element_data=[element_1_data, element_2_data])
    request.addfinalizer(sd.delete_if_exists)
    element.reorder_elements(False, element_2_data, element_1_data)


def test_reorder_unsaved_elements(appliance, request):
    # Automate BZ - https://bugzilla.redhat.com/show_bug.cgi?id=1238721
    element_1_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }
    element_2_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Check Box",
        'default_value': True,
        'field_required': True
    }
    service_dialog = DialogCollection(appliance)
    sd = service_dialog.create(label='label_' + fauxfactory.gen_alphanumeric(),
        description="my dialog", submit=True, cancel=True,)
    tab = sd.tabs.create(tab_label='tab_' + fauxfactory.gen_alphanumeric(),
        tab_desc="my tab desc")
    box = tab.boxes.create(box_label='box_' + fauxfactory.gen_alphanumeric(),
        box_desc="my box desc")
    element = box.elements.create(element_data=[element_1_data])
    request.addfinalizer(sd.delete_if_exists)
    element.reorder_elements(True, element_2_data, element_1_data)
