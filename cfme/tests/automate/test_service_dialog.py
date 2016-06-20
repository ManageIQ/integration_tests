# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from utils.update import update
from utils import error
from cfme.automate.service_dialogs import ServiceDialog


pytestmark = [pytest.mark.tier(3)]


def test_create_service_dialog():
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }
    dialog = ServiceDialog(label=fauxfactory.gen_alphanumeric(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                           tab_desc="my tab desc",
                           box_label="box_" + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    dialog.create(element_data)


def test_update_service_dialog():
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }
    dialog = ServiceDialog(label=fauxfactory.gen_alphanumeric(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                           tab_desc="my tab desc",
                           box_label="box_" + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    dialog.create(element_data)
    with update(dialog):
        dialog.description = "my edited description"


def test_delete_service_dialog():
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }
    dialog = ServiceDialog(label=fauxfactory.gen_alphanumeric(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                           tab_desc="my tab desc",
                           box_label="box_" + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    dialog.create(element_data)
    dialog.delete()


def test_service_dialog_duplicate_name():
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }
    dialog = ServiceDialog(label=fauxfactory.gen_alphanumeric(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                           tab_desc="my tab desc",
                           box_label="box_" + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    dialog.create(element_data)
    with error.expected("Label has already been taken"):
        dialog.create(element_data)


def test_checkbox_dialog_element():
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Check Box",
        'default_text_box': True,
        'field_required': True
    }
    dialog = ServiceDialog(label=fauxfactory.gen_alphanumeric(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                           tab_desc="my tab desc",
                           box_label="box_" + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    dialog.create(element_data)


def test_datecontrol_dialog_element():
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Date Control",
        'field_past_dates': True
    }
    dialog = ServiceDialog(label=fauxfactory.gen_alphanumeric(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                           tab_desc="my tab desc",
                           box_label="box_" + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    dialog.create(element_data)


def test_dropdownlist_dialog_element():
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Drop Down List"
    }
    dialog = ServiceDialog(label=fauxfactory.gen_alphanumeric(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                           tab_desc="my tab desc",
                           box_label="box_" + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    dialog.create(element_data)


def test_radiobutton_dialog_element():
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Radio Button"
    }
    dialog = ServiceDialog(label=fauxfactory.gen_alphanumeric(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                           tab_desc="my tab desc",
                           box_label="box_" + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    dialog.create(element_data)


def test_tagcontrol_dialog_element():
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Tag Control",
        'field_category': "Service Level",
        'field_required': True
    }
    dialog = ServiceDialog(label=fauxfactory.gen_alphanumeric(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                           tab_desc="my tab desc",
                           box_label="box_" + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    dialog.create(element_data)


def test_textareabox_dialog_element():
    element_data = {
        'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
        'ele_name': fauxfactory.gen_alphanumeric(),
        'ele_desc': fauxfactory.gen_alphanumeric(),
        'choose_type': "Text Area Box",
        'field_required': True
    }
    dialog = ServiceDialog(label=fauxfactory.gen_alphanumeric(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                           tab_desc="my tab desc",
                           box_label="box_" + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    dialog.create(element_data)


def test_reorder_elements():
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
        'default_text_box': True,
        'field_required': True
    }
    dialog = ServiceDialog(label=fauxfactory.gen_alphanumeric(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                           tab_desc="my tab desc",
                           box_label="box_" + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    dialog.create(element_1_data, element_2_data)
    dialog.reorder_elements(dialog.tab_label, dialog.box_label, element_1_data, element_2_data)


def test_reorder_unsaved_elements():
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
        'default_text_box': True,
        'field_required': True
    }
    dialog = ServiceDialog(label=fauxfactory.gen_alphanumeric(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                           tab_desc="my tab desc",
                           box_label="box_" + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    dialog.create(element_1_data)
    dialog.update_element(element_2_data, element_1_data)
